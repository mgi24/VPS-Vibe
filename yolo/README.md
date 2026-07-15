# YOLO Object Detection Demo

Demo object detection running on port 8004.

## Models

| Endpoint | Model | Type |
|---|---|---|
| `POST /detect` | `yolov8s.pt` | Object detection |
| `POST /segment` | `yolo11n-seg.pt` | Segmentation |
| `POST /prompt-segment` | `facebook/sam-vit-base` | Prompt-based segmentation (SAM) |
| `POST /cs2-segment` | `cs2-s-26last.pt` | CS2 segmentation |

## Prompt Segment (SAM)

Interactive prompt-based segmentation using [SAM (Segment Anything Model)](https://huggingface.co/facebook/sam-vit-base) from Meta/Facebook.

- Upload or drag-drop an image
- Click points on the image (foreground or background) to guide segmentation
- Adjust confidence, image size, and IoU thresholds
- API: `POST /prompt-segment` with JSON body `{ base64, points, point_labels }`

## Model Loading

Models are loaded at startup and always stay in memory (`model_always_on.py`).

An alternative idle-offload version is available in `model_manager.py` —
models are lazily loaded on first request and unloaded after 60s of
inactivity to save RAM. To use it, swap the import in `main.py` from
`model_always_on` to `model_manager`.
