import base64
import logging
import time
from pathlib import Path

import uvicorn

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from model_always_on import (
    model,
    seg_model,
    cs2_model,
    class_names,
    seg_class_names,
    cs2_class_names,
)

BASE_DIR = Path(__file__).parent

REQUEST_DELAY_LIMIT: float = 0.5

app = FastAPI()
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/assets", StaticFiles(directory=str(BASE_DIR / "assets")), name="assets")


class DetectRequest(BaseModel):
    base64: str
    conf: float | None = None
    iou: float | None = None
    imgsz: int | None = None


class PromptSegmentRequest(BaseModel):
    base64: str
    points: list[list[int]] | None = None
    point_labels: list[int] | None = None


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


def draw_detections(img: np.ndarray, results, class_names: dict) -> np.ndarray:
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


def draw_segmentations(img: np.ndarray, results, class_names: dict) -> np.ndarray:
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
            label = f"{class_names[cls_id]} {conf:.2f}"
            color = get_color(cls_id)
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(img, (x1, y1 - th - 8), (x1 + tw + 8, y1), color, -1)
            cv2.putText(img, label, (x1 + 4, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.addWeighted(overlay, 0.35, img, 0.65, 0, img)
    return img


def draw_sam_masks(img: np.ndarray, mask: np.ndarray, points: list[list[int]] | None = None) -> np.ndarray:
    overlay = img.copy()
    mask_bool = mask.astype(bool)
    color = (0, 200, 150)
    colored_mask = np.zeros_like(img)
    colored_mask[mask_bool] = color
    cv2.addWeighted(colored_mask, 0.5, overlay, 0.5, 0, overlay)
    mask_uint8 = (mask_bool * 255).astype(np.uint8)
    contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(overlay, contours, -1, (0, 255, 200), 2)
    if points:
        for pt in points:
            cv2.circle(overlay, tuple(pt), 6, (0, 255, 0), -1)
            cv2.circle(overlay, tuple(pt), 6, (255, 255, 255), 2)
    return overlay


def decode_image(req: DetectRequest):
    try:
        image_data = base64.b64decode(req.base64)
        np_arr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image data")
        return img
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image data")


def build_kwargs(req: DetectRequest) -> dict:
    kwargs = {}
    if req.conf is not None:
        kwargs["conf"] = req.conf
    if req.iou is not None:
        kwargs["iou"] = req.iou
    if req.imgsz is not None:
        kwargs["imgsz"] = req.imgsz
    return kwargs


def detection_results(results, class_names: dict):
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
    return detections


def encode_result(img: np.ndarray) -> str:
    _, buffer = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.b64encode(buffer).decode("utf-8")


def check_rate_limit(client_ip: str):
    if REQUEST_DELAY_LIMIT > 0:
        now = time.time()
        last = session_last_time.get(client_ip, 0)
        if now - last < REQUEST_DELAY_LIMIT:
            raise HTTPException(status_code=429, detail="Rate limit: 1 FPS")
        session_last_time[client_ip] = now


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {})


@app.get("/segment", response_class=HTMLResponse)
async def segment_page(request: Request):
    return templates.TemplateResponse(request, "segment.html", {})


@app.post("/segment")
async def segment(req: DetectRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip)

    img = decode_image(req)
    kwargs = build_kwargs(req)

    results = seg_model(img, **kwargs)
    drawn = draw_segmentations(img.copy(), results, seg_class_names)

    return JSONResponse({
        "image": encode_result(drawn),
        "detections": detection_results(results, seg_class_names),
    })


@app.get("/prompt-segment", response_class=HTMLResponse)
async def prompt_segment_page(request: Request):
    return templates.TemplateResponse(request, "prompt_segment.html", {})


@app.post("/prompt-segment")
async def prompt_segment(req: PromptSegmentRequest, request: Request):
    from model_always_on import get_sam_base
    import torch

    img = decode_image(req)

    if req.points and len(req.points) > 0:
        sam_model, sam_processor = get_sam_base()

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        point_labels = req.point_labels if req.point_labels else [1] * len(req.points)

        inputs = sam_processor(
            img_rgb,
            input_points=[[req.points]],
            input_labels=[point_labels],
            return_tensors="pt",
        )

        with torch.no_grad():
            outputs = sam_model(**inputs)

        masks = sam_processor.image_processor.post_process_masks(
            outputs.pred_masks,
            inputs["original_sizes"],
            inputs["reshaped_input_sizes"],
        )

        best_mask = masks[0][0, 0].cpu().numpy()
        drawn = draw_sam_masks(img.copy(), best_mask, req.points)

        return JSONResponse({
            "image": encode_result(drawn),
            "points": req.points,
        })
    else:
        return JSONResponse({
            "image": encode_result(img),
            "points": [],
        })


@app.get("/cs2-segment", response_class=HTMLResponse)
async def cs2_segment_page(request: Request):
    return templates.TemplateResponse(request, "cs2_segment.html", {})


@app.post("/cs2-segment")
async def cs2_segment(req: DetectRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip)

    img = decode_image(req)
    kwargs = build_kwargs(req)

    results = cs2_model(img, **kwargs)
    drawn = draw_segmentations(img.copy(), results, cs2_class_names)

    return JSONResponse({
        "image": encode_result(drawn),
        "detections": detection_results(results, cs2_class_names),
    })


@app.post("/detect")
async def detect(req: DetectRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip)

    img = decode_image(req)
    kwargs = build_kwargs(req)

    results = model(img, **kwargs)
    drawn = draw_detections(img.copy(), results, class_names)

    return JSONResponse({
        "image": encode_result(drawn),
        "detections": detection_results(results, class_names),
    })


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8004,
        log_level="info",
        access_log=True,
    )
