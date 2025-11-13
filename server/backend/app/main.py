# app/main.py
from dotenv import load_dotenv
load_dotenv()

import asyncio
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.routers import chatbot_router

# Socket.IO가 있으면 마운트, 없으면 건너뜀
try:
    from app.sockets.chat_server import sio_app
    _HAS_SOCKET = True
except Exception:
    sio_app = None
    _HAS_SOCKET = False

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="Investment Mentor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    try:
        body_bytes = await request.body()
        preview = body_bytes.decode("utf-8", errors="ignore")
        if len(preview) > 500:
            preview = preview[:500] + "...(trimmed)"
    except Exception:
        preview = "<unreadable>"
    logger.info(f"[REQ] {request.method} {request.url.path} body={preview}")

    resp = await call_next(request)
    logger.info(f"[RES] {request.method} {request.url.path} -> {resp.status_code}")
    return resp

# 라우터
app.include_router(chatbot_router.router)

# Socket.IO (있는 경우만)
if _HAS_SOCKET and sio_app is not None:
    app.mount("/ws", sio_app)

@app.get("/")
async def root():
    return {"message": "API 서버가 실행 중입니다."}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
