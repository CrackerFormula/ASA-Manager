import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

SCHEDULE_FILE = Path("/serverdata/config/schedule.json")


class Scheduler:
    def __init__(self, path: Path = SCHEDULE_FILE):
        self._path = path
        self._tasks: list[asyncio.Task] = []
        self._running = False

    def _ensure_dir(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def get_schedule(self) -> list[str]:
        if not self._path.exists():
            return []
        try:
            data = json.loads(self._path.read_text())
            return data.get("restart_times", [])
        except (json.JSONDecodeError, KeyError):
            return []

    def set_schedule(self, times: list[str]) -> None:
        # Validate HH:MM format
        for t in times:
            parts = t.split(":")
            if len(parts) != 2:
                raise ValueError(f"Invalid time format: {t!r} (expected HH:MM)")
            try:
                h, m = int(parts[0]), int(parts[1])
                if not (0 <= h <= 23 and 0 <= m <= 59):
                    raise ValueError
            except ValueError:
                raise ValueError(f"Invalid time format: {t!r} (expected HH:MM)")
        self._ensure_dir()
        self._path.write_text(json.dumps({"restart_times": times}, indent=2))
        logger.info("Schedule set to: %s", times)

    def clear_schedule(self) -> None:
        self.set_schedule([])
        logger.info("Schedule cleared")

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
        triggered: set[str] = set()
        while self._running:
            try:
                now = datetime.now(timezone.utc)
                current_time = now.strftime("%H:%M")
                times = self.get_schedule()

                # Reset triggered set at the start of each minute
                if current_time not in triggered:
                    triggered.clear()

                if current_time in times and current_time not in triggered:
                    triggered.add(current_time)
                    logger.info("Scheduled restart triggered at %s UTC", current_time)
                    try:
                        from app.server_manager import server_manager
                        await server_manager.restart()
                        logger.info("Scheduled restart completed")
                    except Exception:
                        logger.exception("Scheduled restart failed")

                await asyncio.sleep(30)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Scheduler loop error")
                await asyncio.sleep(60)


scheduler = Scheduler()
