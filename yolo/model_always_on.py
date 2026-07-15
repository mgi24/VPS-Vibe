import logging
from pathlib import Path

from ultralytics import YOLO

BASE_DIR = Path(__file__).parent

model = YOLO(BASE_DIR / "yolov8s.pt")
class_names = model.names
logging.info("Model 'detect' loaded from yolov8s.pt")

seg_model = YOLO(BASE_DIR / "yolo11n-seg.pt")
seg_class_names = seg_model.names
logging.info("Model 'segment' loaded from yolo11n-seg.pt")

cs2_model = YOLO(BASE_DIR / "cs2-s-26last.pt")
cs2_class_names = cs2_model.names
logging.info("Model 'cs2_segment' loaded from cs2-s-26last.pt")

_sam3_predictor = None

def get_sam3_predictor():
    global _sam3_predictor
    if _sam3_predictor is None:
        from ultralytics.models.sam import SAM3SemanticPredictor
        overrides = dict(
            conf=0.25,
            task="segment",
            mode="predict",
            model=str(BASE_DIR / "sam3.1.pt"),
        )
        _sam3_predictor = SAM3SemanticPredictor(overrides=overrides)
        logging.info("SAM3.1 semantic predictor loaded")
    return _sam3_predictor
