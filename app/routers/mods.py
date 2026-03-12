from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.mod_manager import mod_manager

router = APIRouter(prefix="/api/mods", tags=["mods"])


class ModListBody(BaseModel):
    mod_ids: list[str]


@router.get("")
async def get_mods():
    return {"mod_ids": mod_manager.get_mods()}


@router.post("")
async def set_mods(body: ModListBody):
    try:
        mod_manager.set_mods(body.mod_ids)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"status": "ok", "mod_ids": mod_manager.get_mods()}


@router.delete("/{mod_id}")
async def remove_mod(mod_id: str):
    try:
        mods = mod_manager.remove_mod(mod_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"status": "ok", "mod_ids": mods}
