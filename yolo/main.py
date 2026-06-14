import asyncio
import base64
import io
import logging
import sys
import time
from pathlib import Path

import uvicorn

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from ultralytics import YOLO

BASE_DIR = Path(__file__).parent

REQUEST_DELAY_LIMIT: float = 0.5

model = YOLO(BASE_DIR / "yolov8s.pt")
class_names = model.names

seg_model = YOLO(BASE_DIR / "yolo11n-seg.pt")
seg_class_names = seg_model.names

app = FastAPI()
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/assets", StaticFiles(directory=str(BASE_DIR / "assets")), name="assets")

class DetectRequest(BaseModel):
    base64: str
    conf: float | None = None
    iou: float | None = None
    imgsz: int | None = None

session_last_time: dict[str, float] = {}

COLORS = [
    (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
    (255, 0, 255), (0, 255, 255), (128, 0, 0), (0, 128, 0),
    (0, 0, 128), (128, 128, 0), (128, 0, 128), (0, 128, 128),
    (64, 0, 0), (0, 64, 0), (0, 0, 64), (192, 0, 0),
    (0, 192, 0), (0, 0, 192), (64, 64, 0), (64, 0, 64),
    (0, 64, 64), (192, 192, 0), (192, 0, 192), (0, 192, 192),
    (255, 128, 0), (255, 0, 128), (128, 255, 0), (0, 255, 128),
    (128, 0, 255), (0, 128, 255),
]

def get_color(class_id: int):
    return COLORS[class_id % len(COLORS)]

def draw_detections(img: np.ndarray, results) -> np.ndarray:
    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            label = f"{class_names[cls_id]} {conf:.2f}"
            color = get_color(cls_id)
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(img, (x1, y1 - th - 8), (x1 + tw + 8, y1), color, -1)
            cv2.putText(img, label, (x1 + 4, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    return img

def draw_segmentations(img: np.ndarray, results) -> np.ndarray:
    overlay = img.copy()
    for r in results:
        if r.masks is not None:
            for mask, box in zip(r.masks.xy, r.boxes):
                cls_id = int(box.cls[0])
                color = get_color(cls_id)
                pts = np.array(mask, dtype=np.int32).reshape((-1, 1, 2))
                cv2.fillPoly(overlay, [pts], color)
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            label = f"{seg_class_names[cls_id]} {conf:.2f}"
            color = get_color(cls_id)
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(img, (x1, y1 - th - 8), (x1 + tw + 8, y1), color, -1)
            cv2.putText(img, label, (x1 + 4, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.addWeighted(overlay, 0.35, img, 0.65, 0, img)
    return img

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {})

@app.get("/segment", response_class=HTMLResponse)
async def segment_page(request: Request):
    return templates.TemplateResponse(request, "segment.html", {})

@app.post("/segment")
async def segment(req: DetectRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"

    if REQUEST_DELAY_LIMIT > 0:
        now = time.time()
        last = session_last_time.get(client_ip, 0)
        if now - last < REQUEST_DELAY_LIMIT:
            raise HTTPException(status_code=429, detail="Rate limit: 1 FPS")
        session_last_time[client_ip] = now

    try:
        image_data = base64.b64decode(req.base64)
        np_arr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image data")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image data")

    kwargs = {}
    if req.conf is not None:
        kwargs["conf"] = req.conf
    if req.iou is not None:
        kwargs["iou"] = req.iou
    if req.imgsz is not None:
        kwargs["imgsz"] = req.imgsz

    results = seg_model(img, **kwargs)

    drawn = draw_segmentations(img.copy(), results)

    _, buffer = cv2.imencode(".jpg", drawn, [cv2.IMWRITE_JPEG_QUALITY, 85])
    result_b64 = base64.b64encode(buffer).decode("utf-8")

    detections = []
    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            detections.append({
                "class": seg_class_names[cls_id],
                "class_id": cls_id,
                "confidence": round(float(box.conf[0]), 4),
                "bbox": [int(x) for x in box.xyxy[0].tolist()],
            })

    return JSONResponse({
        "image": result_b64,
        "detections": detections,
    })

@app.post("/detect")
async def detect(req: DetectRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"

    if REQUEST_DELAY_LIMIT > 0:
        now = time.time()
        last = session_last_time.get(client_ip, 0)
        if now - last < REQUEST_DELAY_LIMIT:
            raise HTTPException(status_code=429, detail="Rate limit: 1 FPS")
        session_last_time[client_ip] = now

    try:
        image_data = base64.b64decode(req.base64)
        np_arr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image data")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image data")

    kwargs = {}
    if req.conf is not None:
        kwargs["conf"] = req.conf
    if req.iou is not None:
        kwargs["iou"] = req.iou
    if req.imgsz is not None:
        kwargs["imgsz"] = req.imgsz

    results = model(img, **kwargs)

    drawn = draw_detections(img.copy(), results)

    _, buffer = cv2.imencode(".jpg", drawn, [cv2.IMWRITE_JPEG_QUALITY, 85])
    result_b64 = base64.b64encode(buffer).decode("utf-8")

    detections = []
    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            detections.append({
                "class": class_names[cls_id],
                "class_id": cls_id,
                "confidence": round(float(box.conf[0]), 4),
                "bbox": [int(x) for x in box.xyxy[0].tolist()],
            })

    return JSONResponse({
        "image": result_b64,
        "detections": detections,
    })

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8004,
        log_level="info",
        access_log=True,
    )
