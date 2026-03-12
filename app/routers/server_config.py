from fastapi import APIRouter
from pydantic import BaseModel

from app.server_config import server_config

router = APIRouter(prefix="/api/server-config", tags=["server-config"])


class ServerConfigBody(BaseModel):
    config: dict[str, str]


@router.get("")
async def get_server_config():
    return {"config": server_config.get_config()}


@router.post("")
async def set_server_config(body: ServerConfigBody):
    updated = server_config.set_config(body.config)
    return {"status": "ok", "config": updated}
