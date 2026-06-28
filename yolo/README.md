# YOLO Object Detection Demo

Demo object detection running on port 8004.

## Models

| Endpoint | Model | Type |
|---|---|---|
| `POST /detect` | `yolov8s.pt` | Object detection |
| `POST /segment` | `yolo11n-seg.pt` | Segmentation |
| `POST /cs2-segment` | `cs2-s-26best.pt` | CS2 segmentation |

## Model Loading

Models are loaded at startup and always stay in memory (`model_always_on.py`).

An alternative idle-offload version is available in `model_manager.py` —
models are lazily loaded on first request and unloaded after 60s of
inactivity to save RAM. To use it, swap the import in `main.py` from
`model_always_on` to `model_manager`.
