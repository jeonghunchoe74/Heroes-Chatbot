# app/main.py
import os
import uuid
import logging
from pathlib import Path

from dotenv import load_dotenv

# ── .env 로드 (backend 루트 기준) ────────────────────────────────
_DOTENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=_DOTENV_PATH, override=True)

# ── (윈도우) 이벤트 루프 정책 설정 ───────────────────────────────
try:
    import asyncio
    if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
except Exception:
    pass

from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import uvicorn

# 라우터 안전하게 임포트 (두 구조 모두 대응)
try:
    from app.routers.chatbot_router import router as chatbot_router
except ImportError:
    from app.routers import chatbot_router as _chatbot_router_module
    chatbot_router = _chatbot_router_module.router  # type: ignore

try:
    from app.routers.insight_router import router as insight_router
except ImportError:
    insight_router = None

# ✅ 새로 추가: 뉴스 라우터 (없어도 실행되게 방어)
try:
    from app.routers.news_router import router as news_router
except ImportError:
    news_router = None

# Socket.IO 래퍼 (없어도 실행되게)
try:
    from app.sockets.chat_server import get_sio_app
    _HAS_SOCKET = True
except Exception:
    get_sio_app = None  # type: ignore
    _HAS_SOCKET = False

# ── 로깅 설정 ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("uvicorn.error")
logging.getLogger("app.services.chatbot_service").setLevel(logging.INFO)
logging.getLogger("app.services.sector").setLevel(logging.INFO)

# ── FastAPI 앱 생성 ──────────────────────────────────────────────
fastapi_app = FastAPI(title="Investment Mentor API")

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 업로드 디렉터리 및 정적 서빙 설정 (backend/app/uploads)
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
fastapi_app.mount("/files", StaticFiles(directory=str(UPLOAD_DIR)), name="files")


# ── 요청/응답 로깅 미들웨어 ──────────────────────────────────────
@fastapi_app.middleware("http")
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
@fastapi_app.on_event("startup")
async def _log_env_on_start():
    kiwoom_token = os.getenv("KIWOOM_ACCESS_TOKEN") or ""
    openai_key = os.getenv("OPENAI_API_KEY") or ""
    naver_client_id = os.getenv("NAVER_CLIENT_ID") or ""
    naver_client_secret = os.getenv("NAVER_CLIENT_SECRET") or ""
    logger.info(f"[ENV] .env loaded from: {_DOTENV_PATH}")
    logger.info(
        f"[ENV] KIWOOM_ACCESS_TOKEN prefix: "
        f"{kiwoom_token[:10] if kiwoom_token else '(empty)'}"
    )
    logger.info(
        f"[ENV] OPENAI_API_KEY prefix: "
        f"{openai_key[:10] if openai_key else '(empty)'}"
    )
    logger.info(
        f"[ENV] NAVER_CLIENT_ID: "
        f"{'(set)' if naver_client_id else '(empty - news will use fallback)'}"
    )
    logger.info(
        f"[ENV] NAVER_CLIENT_SECRET: "
        f"{'(set)' if naver_client_secret else '(empty - news will use fallback)'}"
    )


# ── 라우터 등록 ──────────────────────────────────────────────────
fastapi_app.include_router(chatbot_router, prefix="")

if insight_router is not None:
    fastapi_app.include_router(insight_router, prefix="")

# ✅ 새로 추가: /news, /news/{guru_id}
if news_router is not None:
    # news_router 내부에 prefix="/news" 이미 있으니까 prefix 더 안 붙임
    fastapi_app.include_router(news_router)


# ── 헬스체크 및 기본 라우트 ──────────────────────────────────────
@fastapi_app.get("/")
async def root():
    return {"message": "API 서버가 실행 중입니다."}


@fastapi_app.get("/ping")
def ping():
    return {"pong": True}


# ── 파일 업로드 엔드포인트 (PDF/파일 카드 + AI 분석 트리거) ───────
@fastapi_app.post("/upload")
async def upload(
    file: UploadFile = File(...),
    user: str = Form("익명"),
    sid: str = Form(None),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    uid = f"{uuid.uuid4().hex}{ext}"
    save_path = UPLOAD_DIR / uid

    content = await file.read()
    save_path.write_bytes(content)

    url = f"/files/{uid}"
    meta = {
        "id": uid,
        "name": file.filename,
        "size": len(content),
        "mime": file.content_type or "application/octet-stream",
        "url": url,
        "user": user,
    }

    # 텍스트 추출 (미리보기 + 전체 텍스트)
    from app.services.file_service import extract_text_preview, extract_full_text

    preview_text = extract_text_preview(save_path, mime=meta["mime"])
    full_text = extract_full_text(save_path, mime=meta["mime"])
    meta["preview"] = preview_text
    if full_text:
        # 서버 내부 용도 (AI 분석용)
        meta["full_text"] = full_text
    if sid:
        meta["sid"] = sid

    # 업로드 직후, 현재 방 참여자에게만 파일 카드 방송
    try:
        import time
        from app.sockets.chat_server import sio, get_user_room, analyze_file_with_ai

        await sio.emit(
            "file_shared",
            {
                "type": "file",
                "msg": {
                    "sender": {"sid": sid or "http", "name": meta["user"]},
                    "file": {
                        "id": meta["id"],
                        "name": meta["name"],
                        "size": meta["size"],
                        "mime": meta["mime"],
                        "url": meta["url"],
                    },
                    "preview": meta.get("preview") or "",
                    "ts": int(time.time() * 1000),
                },
            },
            room=get_user_room(sid or ""),
        )

        # 선택적으로 AI 분석 트리거 (PDF 등)
        try:
            await analyze_file_with_ai(meta)
        except Exception:
            # 분석 실패는 업로드 흐름에 영향 X
            pass
    except Exception:
        # 방송 실패가 업로드 자체를 막진 않음
        pass

    return JSONResponse(meta, status_code=200)


# ── 최종 ASGI 앱 (Socket.IO 래핑) ─────────────────────────────────
if _HAS_SOCKET and get_sio_app is not None:
    app = get_sio_app(fastapi_app)
else:
    app = fastapi_app


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
