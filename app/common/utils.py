from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from .config import cfg


async def verify_telegram_secret(request: Request) -> None:
    header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if header_secret != cfg.TELEGRAM_SECRET:
        raise HTTPException(status_code=401, detail="NOT VERIFIED")


async def server_error(request, exc) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


exception_handlers = {500: server_error}
