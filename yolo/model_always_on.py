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

cs2_model = YOLO(BASE_DIR / "cs2-s-26best.pt")
cs2_class_names = cs2_model.names
logging.info("Model 'cs2_segment' loaded from cs2-s-26best.pt")
