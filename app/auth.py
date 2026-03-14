import hashlib
import hmac
import logging

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from itsdangerous import TimestampSigner, BadSignature, SignatureExpired
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

logger = logging.getLogger(__name__)

# Derive SECRET_KEY deterministically so sessions survive container restarts.
# Prefer explicit SECRET_KEY env var; fall back to deriving from WEB_PASSWORD.
if settings.SECRET_KEY:
    SECRET_KEY = settings.SECRET_KEY
else:
    SECRET_KEY = hashlib.sha256(f"asa-manager-{settings.WEB_PASSWORD}".encode()).hexdigest()
signer = TimestampSigner(SECRET_KEY)

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def create_session_cookie() -> str:
    return signer.sign("authenticated").decode("utf-8")


def verify_session_cookie(cookie_value: str) -> bool:
    try:
        signer.unsign(cookie_value, max_age=settings.SESSION_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False


async def require_auth(request: Request) -> None:
    cookie = request.cookies.get("session")
    if not cookie or not verify_session_cookie(cookie):
        raise HTTPException(status_code=401, detail="Not authenticated")


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest):
    if not hmac.compare_digest(body.password, settings.WEB_PASSWORD):
        logger.warning("Failed login attempt from %s", request.client.host)
        raise HTTPException(status_code=401, detail="Invalid password")

    response = JSONResponse({"status": "ok"})
    response.set_cookie(
        key="session",
        value=create_session_cookie(),
        httponly=True,
        secure=settings.SECURE_COOKIES,
        samesite="strict",
        max_age=settings.SESSION_MAX_AGE,
        path="/",
    )
    logger.info("Successful login from %s", request.client.host)
    return response


@router.post("/logout")
async def logout():
    response = JSONResponse({"status": "ok"})
    response.delete_cookie(key="session", path="/")
    return response


@router.get("/check")
async def check_auth(request: Request):
    cookie = request.cookies.get("session")
    if not cookie or not verify_session_cookie(cookie):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"status": "authenticated"}
