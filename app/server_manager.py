import asyncio
import logging
import os
import time
from typing import Optional

from app import supervisor_client
from app.config import settings
from app.log_manager import log_manager
from app.rcon_client import RconClient

logger = logging.getLogger(__name__)


class ServerManager:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._stopping = False
        self._stop_task: Optional[asyncio.Task] = None
        self._install_log_task: Optional[asyncio.Task] = None

    async def is_running(self) -> bool:
        return await supervisor_client.is_process_running()

    async def start(self) -> dict:
        async with self._lock:
            if self._stopping:
                return {"status": "error", "message": "Server is currently stopping"}
            if await self.is_running():
                return {"status": "already_running", "message": "Server is already running"}
            try:
                await supervisor_client.start_process()
                logger.info("ARK server started via supervisord")
                return {"status": "started", "message": "Server started"}
            except Exception as e:
                logger.exception("Failed to start ARK server")
                return {"status": "error", "message": str(e)}

    async def _rcon(self, cmd: str) -> Optional[str]:
        if not settings.RCON_ENABLED:
            return None
        try:
            async with RconClient("127.0.0.1", settings.RCON_PORT, settings.SERVER_ADMIN_PASSWORD) as rcon:
                return await rcon.send_command(cmd)
        except Exception:
            logger.warning("RCON command '%s' failed", cmd, exc_info=True)
            return None

    async def _do_stop(self) -> dict:
        async with self._lock:
            if not await self.is_running():
                self._stopping = False
                return {"status": "not_running", "message": "Server is not running"}

            try:
                logger.info("Saving world before stop...")
                save_result = await self._rcon("saveworld")
                logger.info("saveworld result: %s", save_result)
                await asyncio.sleep(5)

                logger.info("Sending doexit command...")
                exit_result = await self._rcon("doexit")
                logger.info("doexit result: %s", exit_result)
                await asyncio.sleep(10)

                # If process is still running, stop via supervisord
                if await self.is_running():
                    logger.info("Process still running after RCON doexit, stopping via supervisord...")
                    try:
                        await supervisor_client.stop_process()
                    except Exception:
                        logger.warning("supervisord stop_process failed (process may have already exited)")
                    await asyncio.sleep(5)

                # Kill any lingering Wine/Proton processes
                await self._kill_wine_processes()

                logger.info("ARK server stopped")
                return {"status": "stopped", "message": "Server stopped"}
            finally:
                self._stopping = False

    async def _kill_wine_processes(self) -> None:
        """Kill lingering Wine/Proton processes that may survive after stop."""
        for proc_name in ("wineserver", "wine64-preloader", "ArkAscendedServer.exe"):
            try:
                kill = await asyncio.create_subprocess_exec(
                    "killall", "-9", proc_name,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await kill.wait()
            except Exception:
                pass

    async def stop(self) -> dict:
        # Check state under lock to prevent race conditions
        async with self._lock:
            if self._stopping:
                return {"status": "stopping", "message": "Server stop already in progress"}
            if not await self.is_running():
                return {"status": "not_running", "message": "Server is not running"}
            self._stopping = True

        self._stop_task = asyncio.create_task(self._do_stop())
        self._stop_task.add_done_callback(self._on_stop_done)
        return {"status": "stopping", "message": "Server stop initiated"}

    def _on_stop_done(self, task: asyncio.Task):
        self._stop_task = None
        exc = task.exception()
        if exc:
            logger.error("Stop task failed: %s", exc)

    async def restart(self) -> dict:
        stop_result = await self._do_stop()
        if stop_result.get("status") == "error":
            return {"status": "error", "message": f"Stop failed: {stop_result.get('message')}", "stop": stop_result}
        start_result = await self.start()
        if start_result.get("status") == "error":
            return {"status": "error", "message": f"Start failed: {start_result.get('message')}", "start": start_result}
        return {"status": "restarted", "stop": stop_result, "start": start_result}

    async def status(self) -> dict:
        try:
            info = await supervisor_client.get_process_info()
        except Exception:
            logger.exception("Failed to get process info from supervisord")
            return {
                "running": False,
                "stopping": self._stopping,
                "pid": None,
                "uptime_seconds": 0,
                "player_count": 0,
            }

        running = info.get("statename") == "RUNNING"
        pid = info.get("pid", 0) if running else None
        start_time = info.get("start", 0)
        uptime = int(time.time() - start_time) if running and start_time else 0
        player_count = 0

        if running:
            response = await self._rcon("listplayers")
            if response:
                lines = [line for line in response.strip().splitlines() if line.strip()]
                if lines and not lines[0].lower().startswith("no players"):
                    player_count = len(lines)

        return {
            "running": running,
            "stopping": self._stopping,
            "pid": pid,
            "uptime_seconds": uptime,
            "player_count": player_count,
        }

    async def install(self) -> dict:
        if self._lock.locked():
            return {"status": "error", "message": "Another operation is in progress"}
        async with self._lock:
            return await self._do_install()

    async def _do_install(self) -> dict:
        if await self.is_running():
            return {"status": "error", "message": "Cannot install while server is running"}

        steamcmd = "/opt/steamcmd/steamcmd.sh"
        if not os.path.exists(steamcmd):
            steamcmd = "/usr/bin/steamcmd"
        if not os.path.exists(steamcmd):
            return {"status": "error", "message": "SteamCMD not found"}

        cmd = [
            steamcmd,
            "+force_install_dir", settings.SERVER_DIR,
            "+login", "anonymous",
            "+app_update", "2430930", "validate",
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
        logger.warning("Stream drain error", exc_info=True)


server_manager = ServerManager()
