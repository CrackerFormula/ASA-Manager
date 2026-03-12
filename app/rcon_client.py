import asyncio
import struct
from typing import Optional

SERVERDATA_AUTH = 3
SERVERDATA_AUTH_RESPONSE = 2
SERVERDATA_EXECCOMMAND = 2
SERVERDATA_RESPONSE_VALUE = 0

# Sane packet size limits (bytes)
_MIN_PACKET_SIZE = 10
_MAX_PACKET_SIZE = 65536

# Maximum iterations when waiting for auth response
_AUTH_MAX_ITERATIONS = 10


def _pack_packet(packet_id: int, packet_type: int, body: str) -> bytes:
    body_bytes = body.encode("utf-8") + b"\x00\x00"
    size = 4 + 4 + len(body_bytes)
    return struct.pack("<iii", size, packet_id, packet_type) + body_bytes


def _unpack_packet(data: bytes) -> tuple[int, int, int, str]:
    if len(data) < 12:
        raise ValueError("Packet too short")
    size, packet_id, packet_type = struct.unpack_from("<iii", data, 0)
    body = data[12 : 12 + size - 8].rstrip(b"\x00").decode("utf-8", errors="replace")
    return size, packet_id, packet_type, body


class RconClient:
    def __init__(self, host: str, port: int, password: str):
        self.host = host
        self.port = port
        self.password = password
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._packet_id = 0

    def _next_id(self) -> int:
        self._packet_id = (self._packet_id % 2147483647) + 1
        return self._packet_id

    async def connect(self) -> None:
        self._reader, self._writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port),
            timeout=5.0,
        )

    async def authenticate(self) -> None:
        if self._writer is None:
            raise RuntimeError("Not connected")

        auth_id = self._next_id()
        packet = _pack_packet(auth_id, SERVERDATA_AUTH, self.password)
        self._writer.write(packet)
        await self._writer.drain()

        iterations = 0
        while True:
            iterations += 1
            if iterations > _AUTH_MAX_ITERATIONS:
                raise TimeoutError(
                    f"RCON authentication: no auth response after {_AUTH_MAX_ITERATIONS} packets"
                )
            _, resp_id, resp_type, _ = await self._read_packet()
            if resp_type == SERVERDATA_AUTH_RESPONSE:
                break
        if resp_id == -1:
            raise PermissionError("RCON authentication failed: bad password")

    async def _read_packet(self) -> tuple[int, int, int, str]:
        try:
            raw_size = await asyncio.wait_for(self._reader.readexactly(4), timeout=10.0)
        except asyncio.IncompleteReadError as exc:
            raise ConnectionError("Connection closed while reading packet size") from exc

        size = struct.unpack("<i", raw_size)[0]
        if size < _MIN_PACKET_SIZE or size > _MAX_PACKET_SIZE:
            raise ValueError(
                f"RCON packet size {size} out of valid range "
                f"({_MIN_PACKET_SIZE}-{_MAX_PACKET_SIZE})"
            )

        try:
            rest = await asyncio.wait_for(self._reader.readexactly(size), timeout=10.0)
        except asyncio.IncompleteReadError as exc:
            raise ConnectionError("Connection closed while reading packet body") from exc

        full = raw_size + rest
        return _unpack_packet(full)

    async def send_command(self, cmd: str) -> str:
        if self._writer is None:
            raise RuntimeError("Not connected")

        cmd_id = self._next_id()
        mirror_id = self._next_id()

        self._writer.write(_pack_packet(cmd_id, SERVERDATA_EXECCOMMAND, cmd))
        # Send a mirror packet to detect end of multi-packet response
        self._writer.write(_pack_packet(mirror_id, SERVERDATA_EXECCOMMAND, ""))
        await self._writer.drain()

        async def _collect() -> str:
            response_parts: list[str] = []
            while True:
                _, resp_id, resp_type, body = await self._read_packet()
                if resp_id == mirror_id:
                    break
                if resp_id == cmd_id and resp_type == SERVERDATA_RESPONSE_VALUE:
                    response_parts.append(body)
            return "".join(response_parts)

        return await asyncio.wait_for(_collect(), timeout=15.0)

    async def disconnect(self) -> None:
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None
            self._reader = None

    async def __aenter__(self) -> "RconClient":
        await self.connect()
        await self.authenticate()
        return self

    async def __aexit__(self, *_) -> None:
        await self.disconnect()
