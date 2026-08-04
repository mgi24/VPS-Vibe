import asyncio
import base64
import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

import uvicorn

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from model_manager import ModelManager

BASE_DIR = Path(__file__).parent

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

model_manager = ModelManager(check_interval=5.0)
seg_mm = model_manager.register(
    "segment",
    BASE_DIR / "yolo11n-seg.pt",
    idle_timeout=60.0,
)
cs2_mm = model_manager.register(
    "cs2_segment",
    BASE_DIR / "cs2-s-26last.pt",
    idle_timeout=60.0,
)
det_mm = model_manager.register(
    "detect",
    BASE_DIR / "yolov8s.pt",
    idle_timeout=60.0,
)

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
    prompts: list[str]


session_last_time: dict[str, float] = {}
task_store: dict[str, dict] = {}
task_lock = threading.Lock()
executor = threading.Semaphore(1)


class _SamWorker:
    def __init__(self, model_path: str, idle_timeout: float = 60.0):
        self.model_path = model_path
        self.idle_timeout = int(idle_timeout)
        self._process: subprocess.Popen | None = None
        self._lock = threading.Lock()

    def _ensure_running(self):
        if self._process is not None and self._process.poll() is None:
            return
        self._process = subprocess.Popen(
            [sys.executable, str(BASE_DIR / "sam_worker.py"),
             str(self.idle_timeout), self.model_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        logging.info("SAM worker started (PID %d)", self._process.pid)

    def send_request(self, task_id: str, img_path: str, prompts: list[str]) -> dict:
        with self._lock:
            self._ensure_running()
            req = json.dumps({
                "task_id": task_id,
                "image_path": img_path,
                "prompts": prompts,
            })
            self._process.stdin.write((req + "\n").encode())
            self._process.stdin.flush()

            while True:
                line = self._process.stdout.readline()
                if not line:
                    rc = self._process.poll()
                    self._process = None
                    raise RuntimeError(f"SAM worker died (rc={rc})")
                line = line.strip()
                if not line:
                    continue
                try:
                    result = json.loads(line)
                    break
                except json.JSONDecodeError:
                    logging.debug("Worker non-JSON output: %s", line)
                    continue

            if self._process.poll() is not None:
                self._process = None

            return result

    def kill(self):
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                self._process.terminate()
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                logging.info("SAM worker killed (PID %d)", self._process.pid)
            self._process = None

    @property
    def is_alive(self) -> bool:
        return self._process is not None and self._process.poll() is None


sam_worker = _SamWorker(str(BASE_DIR / "sam3.1.pt"), idle_timeout=60.0)

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

    await seg_mm.ensure_loaded()
    results = await seg_mm.predict(img, **kwargs)
    drawn = draw_segmentations(img.copy(), results, seg_mm.class_names)

    return JSONResponse({
        "image": encode_result(drawn),
        "detections": detection_results(results, seg_mm.class_names),
    })


@app.get("/prompt-segment", response_class=HTMLResponse)
async def prompt_segment_page(request: Request):
    return templates.TemplateResponse(request, "prompt_segment.html", {})


@app.post("/prompt-segment")
async def prompt_segment(req: PromptSegmentRequest, request: Request):
    img = decode_image(req)

    if not req.prompts:
        return JSONResponse({
            "image": encode_result(img),
            "elapsed": 0,
        })

    task_id = str(uuid.uuid4())[:12]
    with task_lock:
        task_store[task_id] = {
            "status": "processing",
            "image": None,
            "elapsed": None,
            "error": None,
        }

    logging.info(f"Task {task_id} created | prompts={req.prompts}")
    threading.Thread(target=_run_sam3_task, args=(task_id, img, req.prompts), daemon=True).start()

    return JSONResponse({"task_id": task_id})


def _run_sam3_task(task_id: str, img: np.ndarray, prompts: list[str]):
    t0 = time.time()
    try:
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False, dir="/tmp") as tmp:
            cv2.imwrite(tmp.name, img_rgb)
            tmp_path = tmp.name

        try:
            result = sam_worker.send_request(task_id, tmp_path, prompts)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        elapsed = round(time.time() - t0, 2)
        logging.info(f"Task {task_id} done in {elapsed}s | prompts={prompts}")

        with task_lock:
            task_store[task_id]["status"] = result.get("status", "error")
            task_store[task_id]["image"] = result.get("image")
            task_store[task_id]["elapsed"] = result.get("elapsed", elapsed)
            if result.get("error"):
                task_store[task_id]["error"] = result["error"]

    except Exception as e:
        logging.error(f"Task {task_id} failed: {e}")
        with task_lock:
            task_store[task_id]["status"] = "error"
            task_store[task_id]["error"] = str(e)


@app.get("/prompt-segment/status/{task_id}")
async def prompt_segment_status(task_id: str):
    with task_lock:
        task = task_store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["status"] == "done":
        with task_lock:
            result = {
                "status": "done",
                "image": task["image"],
                "elapsed": task["elapsed"],
            }
            del task_store[task_id]
        return JSONResponse(result)

    if task["status"] == "error":
        with task_lock:
            error_msg = task["error"]
            del task_store[task_id]
        return JSONResponse({"status": "error", "error": error_msg}, status_code=500)

    return JSONResponse({"status": "processing"})


@app.get("/cs2-segment", response_class=HTMLResponse)
async def cs2_segment_page(request: Request):
    return templates.TemplateResponse(request, "cs2_segment.html", {})


@app.post("/cs2-segment")
async def cs2_segment(req: DetectRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip)

    img = decode_image(req)
    kwargs = build_kwargs(req)

    await cs2_mm.ensure_loaded()
    results = await cs2_mm.predict(img, **kwargs)
    drawn = draw_segmentations(img.copy(), results, cs2_mm.class_names)

    return JSONResponse({
        "image": encode_result(drawn),
        "detections": detection_results(results, cs2_mm.class_names),
    })


@app.post("/detect")
async def detect(req: DetectRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip)

    img = decode_image(req)
    kwargs = build_kwargs(req)

    await det_mm.ensure_loaded()
    results = await det_mm.predict(img, **kwargs)
    drawn = draw_detections(img.copy(), results, det_mm.class_names)

    return JSONResponse({
        "image": encode_result(drawn),
        "detections": detection_results(results, det_mm.class_names),
    })


@app.on_event("startup")
async def startup_event():
    await model_manager.start_monitor()

@app.on_event("shutdown")
async def shutdown_event():
    sam_worker.kill()
    await model_manager.stop_monitor()
    model_manager.unload_all()

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8004,
        log_level="info",
        access_log=True,
    )
