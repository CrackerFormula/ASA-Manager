import asyncio
import logging
import os
from collections import deque
from typing import AsyncGenerator

logger = logging.getLogger(__name__)


class LogManager:
    def __init__(self, maxlen: int = 500):
        self._buffer: deque[str] = deque(maxlen=maxlen)
        self._subscribers: list[asyncio.Queue] = []
        self._tail_tasks: list[asyncio.Task] = []

    def _append(self, line: str) -> None:
        self._buffer.append(line)
        dead = []
        for q in self._subscribers:
            try:
                q.put_nowait(line)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self._subscribers.remove(q)

    def get_recent(self, n: int = 100) -> list[str]:
        lines = list(self._buffer)
        return lines[-n:] if n < len(lines) else lines

    async def stream(self) -> AsyncGenerator[str, None]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=200)
        self._subscribers.append(q)
        try:
            while True:
                line = await q.get()
                yield line
        finally:
            try:
                self._subscribers.remove(q)
            except ValueError:
                pass

    async def tail_file(self, path: str, prefix: str = "") -> None:
        """Tail a log file using position-based polling for reliability."""
        while True:
            try:
                # Wait for file to exist
                while not os.path.exists(path):
                    await asyncio.sleep(2)

                try:
                    stat = os.stat(path)
                    open_inode = stat.st_ino
                except OSError:
                    await asyncio.sleep(2)
                    continue

                # Use synchronous file I/O in executor for reliable tailing
                loop = asyncio.get_event_loop()
                pos = 0

                # Load existing content
                def _read_existing():
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                        return content, f.tell()

                content, pos = await loop.run_in_executor(None, _read_existing)
                if content:
                    for line in content.rstrip("\n").split("\n"):
                        stripped = line.rstrip("\r")
                        if stripped:
                            self._append(prefix + stripped)

                # Poll for new content
                partial = ""
                while True:
                    def _read_new(position, leftover):
                        try:
                            size = os.path.getsize(path)
                        except OSError:
                            return None, position, leftover
                        # File was truncated/rotated — reset
                        if size < position:
                            position = 0
                        if size == position:
                            return [], position, leftover
                        with open(path, "r", encoding="utf-8", errors="replace") as f:
                            f.seek(position)
                            new_data = f.read()
                            new_pos = f.tell()
                        # Handle partial lines
                        text = leftover + new_data
                        parts = text.split("\n")
                        # Last element is either empty (line ended with \n) or a partial line
                        remaining = parts[-1]
                        complete_lines = parts[:-1]
                        return complete_lines, new_pos, remaining

                    result = await loop.run_in_executor(None, _read_new, pos, partial)
                    lines, pos, partial = result

                    if lines is None:
                        # File gone
                        logger.debug("Log file gone: %s", path)
                        break

                    for line in lines:
                        stripped = line.rstrip("\r")
                        if stripped:
                            self._append(prefix + stripped)

                    # Check for inode change (log rotation)
                    try:
                        current_inode = os.stat(path).st_ino
                        if current_inode != open_inode:
                            logger.debug("Log rotation detected for %s", path)
                            break
                    except OSError:
                        logger.debug("Log file inaccessible: %s", path)
                        break

                    await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning("Error tailing %s, retrying in 2s", path, exc_info=True)
            await asyncio.sleep(2)

    def start_tailing(self, *paths: str) -> None:
        """Start tailing one or more log files concurrently."""
        for path in paths:
            task = asyncio.create_task(self.tail_file(path))
            self._tail_tasks.append(task)

    def stop(self) -> None:
        for task in self._tail_tasks:
            task.cancel()
        self._tail_tasks.clear()


log_manager = LogManager()
