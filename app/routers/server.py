from fastapi import APIRouter, HTTPException

from app.server_manager import server_manager

router = APIRouter(prefix="/api/server", tags=["server"])


@router.post("/start")
async def start_server():
    result = await server_manager.start()
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@router.post("/stop")
async def stop_server():
    return await server_manager.stop()


@router.post("/restart")
async def restart_server():
    return await server_manager.restart()


@router.get("/status")
async def get_status():
    return await server_manager.status()


@router.post("/install")
async def install_server():
    return await server_manager.install()
