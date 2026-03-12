import asyncio
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.log_manager import log_manager

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("/recent")
async def get_recent_logs(n: int = Query(default=100, ge=1, le=500)):
    return log_manager.get_recent(n)


@router.get("/stream")
async def stream_logs():
    async def event_generator():
        async for line in log_manager.stream():
            yield f"data: {line}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
