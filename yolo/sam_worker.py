import sys
import json
import time
import select
import base64
import logging
import cv2
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [worker] %(message)s", stream=sys.stderr)

_orig_stdout = sys.stdout
sys.stdout = sys.stderr

COLORS = [
    (0, 212, 170), (233, 69, 96), (91, 141, 239),
    (255, 170, 0), (167, 139, 250), (244, 114, 182),
]


def draw_sam_results(img: np.ndarray, results, prompts: list[str]) -> np.ndarray:
    drawn = img.copy()
    if not results or len(results) == 0:
        return drawn
    r = results[0]
    if r.masks is None:
        return drawn
    masks_data = r.masks.data.cpu().numpy()
    orig_h, orig_w = drawn.shape[:2]
    for i, mask in enumerate(masks_data):
        mask_f = mask.astype(np.float32) if mask.dtype == bool else mask
        mask_resized = cv2.resize(mask_f, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)
        color = COLORS[i % len(COLORS)]
        mask_bool = mask_resized > 0.5
        overlay = drawn.copy()
        overlay[mask_bool] = color
        cv2.addWeighted(overlay, 0.5, drawn, 0.5, 0, drawn)
        contours, _ = cv2.findContours(
            mask_bool.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        cv2.drawContours(drawn, contours, -1, color, 3)
        if r.boxes is not None and i < len(r.boxes):
            cls_id = int(r.boxes.cls[i])
            conf = float(r.boxes.conf[i])
            label = f"{prompts[cls_id] if cls_id < len(prompts) else prompts[0]} {conf:.2f}"
            x1, y1, x2, y2 = map(int, r.boxes.xyxy[i])
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(drawn, (x1, y1 - th - 8), (x1 + tw + 8, y1), color, -1)
            cv2.putText(drawn, label, (x1 + 4, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    return drawn


def encode_image(img: np.ndarray) -> str:
    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.b64encode(buf).decode("utf-8")


def send_result(result: dict):
    sys.stdout.write(json.dumps(result) + "\n")
    sys.stdout.flush()


def main():
    if len(sys.argv) < 3:
        sys.exit(1)

    idle_timeout = int(sys.argv[1])
    model_path = sys.argv[2]

    logging.info("Loading SAM model from %s ...", model_path)
    from ultralytics.models.sam import SAM3SemanticPredictor

    predictor = SAM3SemanticPredictor(overrides=dict(
        conf=0.25, task="segment", mode="predict", model=model_path,
    ))

    sys.stdout = _orig_stdout
    logging.info("SAM model loaded. Ready. idle_timeout=%ds", idle_timeout)

    while True:
        ready, _, _ = select.select([sys.stdin], [], [], idle_timeout)
        if not ready:
            logging.info("Idle timeout reached, exiting.")
            break

        line = sys.stdin.readline()
        if not line:
            logging.info("EOF received, exiting.")
            break

        request = json.loads(line)
        task_id = request["task_id"]
        img_path = request["image_path"]
        prompts = request["prompts"]

        t0 = time.time()
        try:
            img_bgr = cv2.imread(img_path)
            if img_bgr is None:
                raise RuntimeError(f"Cannot read image: {img_path}")

            predictor.set_image(img_path)
            results = predictor(text=prompts)
            drawn = draw_sam_results(img_bgr, results, prompts)

            result = {
                "task_id": task_id,
                "status": "done",
                "image": encode_image(drawn),
                "elapsed": round(time.time() - t0, 2),
            }
        except Exception as e:
            logging.error("Task %s failed: %s", task_id, e)
            result = {
                "task_id": task_id,
                "status": "error",
                "error": str(e),
                "elapsed": round(time.time() - t0, 2),
            }

        send_result(result)


if __name__ == "__main__":
    main()
