import asyncio
from collections import deque
from typing import AsyncGenerator


class LogManager:
    def __init__(self, maxlen: int = 500):
        self._buffer: deque[str] = deque(maxlen=maxlen)
        self._subscribers: list[asyncio.Queue] = []
        self._tail_task: asyncio.Task | None = None

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

    async def tail_file(self, path: str) -> None:
        while True:
            try:
                async with _open_and_tail(path, self._append) as _:
                    pass
            except Exception:
                pass
            await asyncio.sleep(2)

    def start_tailing(self, path: str) -> None:
        if self._tail_task is None or self._tail_task.done():
            self._tail_task = asyncio.create_task(self.tail_file(path))

    def stop(self) -> None:
        if self._tail_task:
            self._tail_task.cancel()
            self._tail_task = None


class _open_and_tail:
    """Async context manager that tails a file, handling rotation."""

    def __init__(self, path: str, callback):
        self.path = path
        self.callback = callback

    async def __aenter__(self):
        import aiofiles
        import os

        # Wait for file to exist
        while not os.path.exists(self.path):
            await asyncio.sleep(2)

        self._file = await aiofiles.open(self.path, "r", encoding="utf-8", errors="replace")
        await self._file.seek(0, 2)  # seek to end
        self._run_task = asyncio.create_task(self._run())
        return self

    async def _run(self):
        import aiofiles
        import os

        try:
            while True:
                line = await self._file.readline()
                if line:
                    self.callback(line.rstrip("\n"))
                else:
                    # Check for rotation: file gone or inode changed
                    try:
                        current_inode = os.stat(self.path).st_ino
                        fd_inode = os.fstat(self._file.fileno()).st_ino
                        if current_inode != fd_inode:
                            break
                    except OSError:
                        break
                    await asyncio.sleep(0.25)
        finally:
            await self._file.close()

    async def __aexit__(self, *_):
        self._run_task.cancel()
        try:
            await self._run_task
        except asyncio.CancelledError:
            pass


log_manager = LogManager()
