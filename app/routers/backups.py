from fastapi import APIRouter, HTTPException

from app.backup_manager import backup_manager
from app.server_manager import server_manager

router = APIRouter(prefix="/api/backups", tags=["backups"])


@router.get("")
async def list_backups():
    return {"backups": backup_manager.list_backups()}


@router.post("")
async def create_backup():
    try:
        result = backup_manager.create_backup()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok", **result}


@router.delete("/{filename}")
async def delete_backup(filename: str):
    try:
        backup_manager.delete_backup(filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "ok"}


@router.post("/{filename}/restore")
async def restore_backup(filename: str):
    if await server_manager.is_running():
        raise HTTPException(status_code=409, detail="Server must be stopped before restoring a backup")
    try:
        backup_manager.restore_backup(filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok", "message": f"Backup {filename} restored successfully"}
