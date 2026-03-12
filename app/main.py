import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.auth import limiter, require_auth, router as auth_router, verify_session_cookie
from app.config import settings
from app.log_manager import log_manager
from app.routers import server, settings as settings_router, logs, mods, schedule, backups
from app.scheduler import scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup validation
    if not settings.WEB_PASSWORD:
        logger.critical("=" * 60)
        logger.critical("WEB_PASSWORD is not set. Refusing to start.")
        logger.critical("Set the WEB_PASSWORD environment variable.")
        logger.critical("=" * 60)
        sys.exit(1)

    if settings.SERVER_ADMIN_PASSWORD in ("changeme", ""):
        logger.warning("=" * 60)
        logger.warning("WARNING: SERVER_ADMIN_PASSWORD is '%s'", settings.SERVER_ADMIN_PASSWORD)
        logger.warning("Change this before exposing to the internet!")
        logger.warning("=" * 60)

    log_manager.start_tailing(settings.ARK_LOG_PATH)
    await scheduler.start()
    yield
    await scheduler.stop()
    # Shutdown — gracefully stop ARK if running (handles container SIGTERM)
    from app.server_manager import server_manager
    try:
        if await server_manager.is_running():
            logger.info("Shutdown: initiating graceful ARK server stop...")
            await server_manager._do_stop()
            logger.info("Shutdown: ARK server stopped")
    except Exception:
        logger.exception("Shutdown: failed to gracefully stop ARK server")
    finally:
        log_manager.stop()


app = FastAPI(title="ASA Manager", version="1.0.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth_router)
app.include_router(server.router, dependencies=[Depends(require_auth)])
app.include_router(settings_router.router, dependencies=[Depends(require_auth)])
app.include_router(logs.router, dependencies=[Depends(require_auth)])
app.include_router(mods.router, dependencies=[Depends(require_auth)])
app.include_router(schedule.router, dependencies=[Depends(require_auth)])
app.include_router(backups.router, dependencies=[Depends(require_auth)])

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    cookie = request.cookies.get("session")
    if cookie and verify_session_cookie(cookie):
        return templates.TemplateResponse("index.html", {"request": request})
    return templates.TemplateResponse("login.html", {"request": request})
