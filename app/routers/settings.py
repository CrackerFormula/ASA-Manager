from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Optional

from app.ini_manager import ini_manager

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SingleSetting(BaseModel):
    section: str
    key: Optional[str] = None
    value: Optional[Any] = None
    data: Optional[dict[str, Any]] = None


@router.get("")
async def get_all_settings():
    return ini_manager.read_all()


@router.get("/{section}")
async def get_section(section: str):
    result = ini_manager.read_section(section)
    if not result:
        raise HTTPException(status_code=404, detail=f"Section '{section}' not found")
    return result


@router.post("")
async def write_settings(body: SingleSetting):
    if body.data is not None:
        ini_manager.write_section(body.section, body.data)
        return {"status": "ok", "section": body.section}
    elif body.key is not None and body.value is not None:
        ini_manager.write_setting(body.section, body.key, body.value)
        return {"status": "ok", "section": body.section, "key": body.key}
    else:
        raise HTTPException(status_code=422, detail="Provide either 'key'+'value' or 'data' dict")
