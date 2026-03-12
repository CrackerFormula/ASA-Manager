import asyncio
import logging
import xmlrpc.client
from typing import Any

logger = logging.getLogger(__name__)

SUPERVISOR_SOCKET = "unix:///var/run/supervisor.sock"


def _get_proxy() -> xmlrpc.client.ServerProxy:
    try:
        from supervisor.xmlrpc import SupervisorTransport
        return xmlrpc.client.ServerProxy(
            "http://127.0.0.1",
            transport=SupervisorTransport(None, None, serverurl=SUPERVISOR_SOCKET),
        )
    except ImportError:
        logger.warning("supervisor package not available, using fallback transport")
        import http.client
        import socket

        class UnixTransport(xmlrpc.client.Transport):
            def make_connection(self, host):
                conn = http.client.HTTPConnection("localhost")
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect("/var/run/supervisor.sock")
                conn.sock = sock
                return conn

        return xmlrpc.client.ServerProxy(
            "http://localhost",
            transport=UnixTransport(),
        )


async def start_process(name: str = "arkserver") -> bool:
    def _call():
        proxy = _get_proxy()
        return proxy.supervisor.startProcess(name)
    return await asyncio.to_thread(_call)


async def stop_process(name: str = "arkserver") -> bool:
    def _call():
        proxy = _get_proxy()
        return proxy.supervisor.stopProcess(name)
    return await asyncio.to_thread(_call)


async def get_process_info(name: str = "arkserver") -> dict[str, Any]:
    def _call():
        proxy = _get_proxy()
        return proxy.supervisor.getProcessInfo(name)
    return await asyncio.to_thread(_call)


async def is_process_running(name: str = "arkserver") -> bool:
    try:
        info = await get_process_info(name)
        return info.get("statename") == "RUNNING"
    except Exception:
        logger.exception("Failed to query supervisord for process '%s'", name)
        return False
