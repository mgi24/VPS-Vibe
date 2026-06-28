# YOLO Object Detection Demo

Demo object detection running on port 8004.

## Models

| Endpoint | Model | Type |
|---|---|---|
| `POST /detect` | `yolov8s.pt` | Object detection |
| `POST /segment` | `yolo11n-seg.pt` | Segmentation |
| `POST /cs2-segment` | `cs2-s-26best.pt` | CS2 segmentation |

## Idle Offload

Models are loaded lazily on first request. After 60 seconds of inactivity,
the model is unloaded from memory and automatically reloaded on the next
request. This keeps RAM usage low when the service is idle.

Each model segment (detect, segment, cs2) has its own independent idle timer.
