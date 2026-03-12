import asyncio
import os
import time
from typing import Optional

from app.config import settings
from app.log_manager import log_manager
from app.rcon_client import RconClient


class ServerManager:
    def __init__(self):
        self._process: Optional[asyncio.subprocess.Process] = None
        self._start_time: Optional[float] = None
        self._log_task: Optional[asyncio.Task] = None
        self._install_log_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    def is_running(self) -> bool:
        return self._process is not None and self._process.returncode is None

    async def _read_streams(self) -> None:
        if self._process is None:
            return
        tasks = []
        for stream in (self._process.stdout, self._process.stderr):
            if stream is not None:
                tasks.append(asyncio.create_task(_drain_stream(stream, log_manager._append)))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def start(self) -> dict:
        async with self._lock:
            if self.is_running():
                return {"status": "already_running", "message": "Server is already running"}

            script = "/app/scripts/start_ark.sh"
            if not os.path.exists(script):
                return {"status": "error", "message": f"Start script not found: {script}"}

            self._process = await asyncio.create_subprocess_exec(
                "/bin/bash",
                script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ},
            )
            self._start_time = time.time()
            self._log_task = asyncio.create_task(self._read_streams())
            return {"status": "started", "message": f"Server started with PID {self._process.pid}"}

    async def _rcon(self, cmd: str) -> Optional[str]:
        if not settings.RCON_ENABLED:
            return None
        try:
            async with RconClient("127.0.0.1", settings.RCON_PORT, settings.SERVER_ADMIN_PASSWORD) as rcon:
                return await rcon.send_command(cmd)
        except Exception:
            return None

    async def _do_stop(self) -> dict:
        async with self._lock:
            if not self.is_running():
                return {"status": "not_running", "message": "Server is not running"}

            await self._rcon("saveworld")
            await asyncio.sleep(30)

            await self._rcon("doexit")
            await asyncio.sleep(10)

            if self.is_running():
                try:
                    self._process.terminate()
                except ProcessLookupError:
                    pass
                try:
                    await asyncio.wait_for(self._process.wait(), timeout=15)
                except asyncio.TimeoutError:
                    self._process.kill()

            self._process = None
            self._start_time = None
            if self._log_task:
                self._log_task.cancel()
                self._log_task = None
            return {"status": "stopped", "message": "Server stopped"}

    async def stop(self) -> dict:
        if not self.is_running():
            return {"status": "not_running", "message": "Server is not running"}
        asyncio.create_task(self._do_stop())
        return {"status": "stopping", "message": "Server stop initiated"}

    async def restart(self) -> dict:
        stop_result = await self._do_stop()
        start_result = await self.start()
        return {"status": "restarted", "stop": stop_result, "start": start_result}

    async def status(self) -> dict:
        running = self.is_running()
        pid = self._process.pid if running and self._process else None
        uptime = int(time.time() - self._start_time) if running and self._start_time else 0
        player_count = 0

        if running:
            response = await self._rcon("listplayers")
            if response:
                lines = [l for l in response.strip().splitlines() if l.strip()]
                if lines and not lines[0].lower().startswith("no players"):
                    player_count = len(lines)

        return {
            "running": running,
            "pid": pid,
            "uptime_seconds": uptime,
            "player_count": player_count,
        }

    async def install(self) -> dict:
        if self.is_running():
            return {"status": "error", "message": "Cannot install while server is running"}

        steamcmd = "/usr/bin/steamcmd"
        if not os.path.exists(steamcmd):
            steamcmd = "steamcmd"

        cmd = [
            steamcmd,
            "+force_install_dir", settings.SERVER_DIR,
            "+login", "anonymous",
            "+app_update", "2430930",
            "+quit",
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        self._install_log_task = asyncio.create_task(_drain_stream(proc.stdout, log_manager._append))
        await proc.wait()
        return {"status": "done", "returncode": proc.returncode}


async def _drain_stream(stream: asyncio.StreamReader, callback) -> None:
    try:
        async for line_bytes in stream:
            line = line_bytes.decode("utf-8", errors="replace").rstrip("\n")
            callback(line)
    except Exception:
        pass


server_manager = ServerManager()
