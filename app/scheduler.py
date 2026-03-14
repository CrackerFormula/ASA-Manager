import asyncio
import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

SCHEDULE_FILE = Path("/serverdata/config/schedule.json")
VALID_INTERVALS = [0, 3, 6, 12, 18, 24]


class Scheduler:
    def __init__(self, path: Path = SCHEDULE_FILE):
        self._path = path
        self._tasks: list[asyncio.Task] = []
        self._running = False

    def _ensure_dir(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def get_schedule(self) -> dict:
        if not self._path.exists():
            return {"interval_hours": 0}
        try:
            data = json.loads(self._path.read_text())
            # Migrate old format
            if "restart_times" in data and "interval_hours" not in data:
                return {"interval_hours": 0}
            return {"interval_hours": data.get("interval_hours", 0)}
        except (json.JSONDecodeError, KeyError):
            return {"interval_hours": 0}

    def set_interval(self, hours: int) -> None:
        if hours not in VALID_INTERVALS:
            raise ValueError(f"Invalid interval: {hours}h (valid: {VALID_INTERVALS})")
        self._ensure_dir()
        self._path.write_text(json.dumps({"interval_hours": hours}, indent=2))
        logger.info("Restart interval set to: %dh", hours)

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._tasks = [asyncio.create_task(self._scheduler_loop())]
        logger.info("Scheduler started")

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks.clear()
        logger.info("Scheduler stopped")

    async def _scheduler_loop(self) -> None:
        last_restart = time.monotonic()
        while self._running:
            try:
                schedule = self.get_schedule()
                interval = schedule["interval_hours"]

                if interval > 0:
                    elapsed = time.monotonic() - last_restart
                    remaining = (interval * 3600) - elapsed
                    if remaining <= 0:
                        logger.info("Scheduled restart triggered (every %dh)", interval)
                        try:
                            from app.server_manager import server_manager
                            await server_manager.restart()
                            logger.info("Scheduled restart completed")
                        except Exception:
                            logger.exception("Scheduled restart failed")
                        last_restart = time.monotonic()

                await asyncio.sleep(30)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Scheduler loop error")
                await asyncio.sleep(60)


scheduler = Scheduler()
