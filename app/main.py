from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse

from app.config import settings
from app.log_manager import log_manager
from app.routers import server, settings as settings_router, logs


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    log_manager.start_tailing(settings.ARK_LOG_PATH)
    yield
    # Shutdown
    log_manager.stop()


app = FastAPI(title="ASA Manager", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(server.router)
app.include_router(settings_router.router)
app.include_router(logs.router)

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
