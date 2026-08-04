import asyncio
import gc
import logging
import time
from pathlib import Path

from ultralytics import YOLO


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
        self._check_interval = check_interval
        self._task: asyncio.Task | None = None

    def register(
        self, name: str, model_path: str | Path, idle_timeout: float = 60.0
    ) -> ManagedModel:
        mm = ManagedModel(name, model_path, idle_timeout)
        self._models[name] = mm
        return mm

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
