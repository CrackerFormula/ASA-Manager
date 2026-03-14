from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.scheduler import scheduler

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


class ScheduleBody(BaseModel):
    interval_hours: int


@router.get("")
async def get_schedule():
    return scheduler.get_schedule()


@router.post("")
async def set_schedule(body: ScheduleBody):
    try:
        scheduler.set_interval(body.interval_hours)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    # Restart scheduler loop to pick up new interval
    await scheduler.stop()
    await scheduler.start()
    return scheduler.get_schedule()
