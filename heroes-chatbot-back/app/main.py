# app/main.py
from pathlib import Path
from dotenv import load_dotenv

# .env를 backend 루트에서 강제로 로드
_DOTENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=_DOTENV_PATH, override=True)

# (윈도우) 이벤트 루프 정책 설정 - 비윈도우에서도 안전하게
try:
    import asyncio
    if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
except Exception:
    pass

import os
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

# 로깅 설정 - DEBUG 레벨로 설정하여 섹터 분석 로그 확인 가능
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("uvicorn.error")
# 앱 로거들도 INFO 레벨로 설정
logging.getLogger("app.services.chatbot_service").setLevel(logging.INFO)
logging.getLogger("app.services.sector").setLevel(logging.INFO)

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

# ── 스타트업 시 .env/토큰 확인 로그 ───────────────────────────────
@app.on_event("startup")
async def _log_env_on_start():
    kiwoom_token = os.getenv("KIWOOM_ACCESS_TOKEN") or ""
    openai_key = os.getenv("OPENAI_API_KEY") or ""
    naver_client_id = os.getenv("NAVER_CLIENT_ID") or ""
    naver_client_secret = os.getenv("NAVER_CLIENT_SECRET") or ""
    logger.info(f"[ENV] .env loaded from: {_DOTENV_PATH}")
    logger.info(f"[ENV] KIWOOM_ACCESS_TOKEN prefix: {kiwoom_token[:10] if kiwoom_token else '(empty)'}")
    logger.info(f"[ENV] OPENAI_API_KEY prefix: {openai_key[:10] if openai_key else '(empty)'}")
    logger.info(f"[ENV] NAVER_CLIENT_ID: {'(set)' if naver_client_id else '(empty - news will use fallback)'}")
    logger.info(f"[ENV] NAVER_CLIENT_SECRET: {'(set)' if naver_client_secret else '(empty - news will use fallback)'}")

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
