from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.scheduler import scheduler

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


class ScheduleBody(BaseModel):
    restart_times: list[str]


@router.get("")
async def get_schedule():
    return {"restart_times": scheduler.get_schedule()}


@router.post("")
async def set_schedule(body: ScheduleBody):
    try:
        scheduler.set_schedule(body.restart_times)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    # Restart scheduler loop to pick up new times
    await scheduler.stop()
    await scheduler.start()
    return {"status": "ok", "restart_times": scheduler.get_schedule()}


@router.delete("")
async def clear_schedule():
    scheduler.clear_schedule()
    await scheduler.stop()
    await scheduler.start()
    return {"status": "ok", "restart_times": []}
