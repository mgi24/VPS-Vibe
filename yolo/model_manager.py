import asyncio
import gc
import logging
import threading
import time
from pathlib import Path

from ultralytics import YOLO


class ManagedSAMPredictor:
    """Lazy-load + auto-unload wrapper for SAM3SemanticPredictor."""

    def __init__(self, name: str, model_path: str | Path, idle_timeout: float = 60.0):
        self.name = name
        self.model_path = Path(model_path)
        self.idle_timeout = idle_timeout
        self._predictor = None
        self._last_used = 0.0
        self._busy = False

    def ensure_loaded(self):
        """Must be called from within sam_lock (thread context)."""
        if self._predictor is None:
            from ultralytics.models.sam import SAM3SemanticPredictor

            logging.info("SAM predictor '%s' loading from %s ...", self.name, self.model_path.name)
            overrides = dict(
                conf=0.25,
                task="segment",
                mode="predict",
                model=str(self.model_path),
            )
            self._predictor = SAM3SemanticPredictor(overrides=overrides)
            logging.info("SAM predictor '%s' loaded", self.name)
        self._last_used = time.time()

    @property
    def predictor(self):
        return self._predictor

    def mark_busy(self, busy: bool):
        self._busy = busy

    def mark_used(self):
        self._last_used = time.time()

    def try_unload(self, sam_lock: threading.Lock) -> bool:
        """Attempt unload. Returns True if actually unloaded."""
        if not self.is_loaded:
            return False
        if self._busy:
            logging.info("SAM predictor '%s' still busy, skipping unload", self.name)
            return False
        acquired = sam_lock.acquire(timeout=2)
        if not acquired:
            logging.info("SAM predictor '%s' lock not available, skipping unload", self.name)
            return False
        try:
            if self._predictor is not None:
                del self._predictor
                self._predictor = None
                gc.collect()
                logging.info("SAM predictor '%s' unloaded (idle timeout)", self.name)
                return True
        finally:
            sam_lock.release()
        return False

    @property
    def is_loaded(self):
        return self._predictor is not None

    @property
    def idle_seconds(self):
        if self.is_loaded:
            return time.time() - self._last_used
        return 0.0


class ManagedModel:
    def __init__(self, name: str, model_path: str | Path, idle_timeout: float = 60.0):
        self.name = name
        self.model_path = Path(model_path)
        self.idle_timeout = idle_timeout
        self._model: YOLO | None = None
        self._class_names: dict | None = None
        self._last_used: float = 0.0

    async def ensure_loaded(self):
        if self._model is None:
            loop = asyncio.get_event_loop()
            self._model = await loop.run_in_executor(
                None, lambda: YOLO(str(self.model_path))
            )
            self._class_names = self._model.names
            logging.info(
                "Model '%s' loaded from %s", self.name, self.model_path.name
            )
        self._last_used = time.time()

    async def predict(self, img, **kwargs):
        await self.ensure_loaded()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self._model(img, **kwargs)
        )

    def unload(self):
        if self._model is not None:
            del self._model
            self._model = None
            self._class_names = None
            gc.collect()
            logging.info("Model '%s' unloaded (idle timeout)", self.name)

    @property
    def class_names(self) -> dict | None:
        return self._class_names

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def idle_seconds(self) -> float:
        if self.is_loaded:
            return time.time() - self._last_used
        return 0.0


class ModelManager:
    def __init__(self, check_interval: float = 5.0):
        self._models: dict[str, ManagedModel] = {}
        self._sam_predictors: dict[str, ManagedSAMPredictor] = {}
        self._check_interval = check_interval
        self._task: asyncio.Task | None = None
        self._sam_lock: threading.Lock | None = None

    def register(
        self, name: str, model_path: str | Path, idle_timeout: float = 60.0
    ) -> ManagedModel:
        mm = ManagedModel(name, model_path, idle_timeout)
        self._models[name] = mm
        return mm

    def register_sam(
        self, name: str, model_path: str | Path, idle_timeout: float = 60.0
    ) -> ManagedSAMPredictor:
        sam = ManagedSAMPredictor(name, model_path, idle_timeout)
        self._sam_predictors[name] = sam
        return sam

    def set_sam_lock(self, lock: threading.Lock):
        self._sam_lock = lock

    async def start_monitor(self):
        loop = asyncio.get_running_loop()
        self._task = loop.create_task(self._monitor_loop())

    async def _monitor_loop(self):
        while True:
            try:
                now = time.time()
                for name, mm in self._models.items():
                    if mm.is_loaded and (now - mm._last_used) >= mm.idle_timeout:
                        logging.info(
                            "Model '%s' idle for %.1fs (timeout: %.0fs)",
                            name,
                            now - mm._last_used,
                            mm.idle_timeout,
                        )
                        mm.unload()
                for name, sam in self._sam_predictors.items():
                    if sam.is_loaded and (now - sam._last_used) >= sam.idle_timeout:
                        logging.info(
                            "SAM '%s' idle for %.1fs (timeout: %.0fs)",
                            name,
                            now - sam._last_used,
                            sam.idle_timeout,
                        )
                        if self._sam_lock:
                            sam.try_unload(self._sam_lock)
            except Exception as e:
                logging.error("Monitor error: %s", e, exc_info=True)
            await asyncio.sleep(self._check_interval)

    async def stop_monitor(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def unload_all(self):
        for name, mm in self._models.items():
            if mm.is_loaded:
                logging.info("Unloading model '%s' on shutdown", name)
                mm.unload()
        for name, sam in self._sam_predictors.items():
            if sam.is_loaded and self._sam_lock:
                logging.info("Unloading SAM '%s' on shutdown", name)
                sam.try_unload(self._sam_lock)
