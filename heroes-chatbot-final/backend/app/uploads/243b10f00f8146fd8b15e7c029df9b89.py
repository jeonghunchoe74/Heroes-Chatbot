# app/main.py
import os
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.routers.chatbot_router import router as chatbot_router
from app.routers.insight_router import router as insight_router
from app.sockets.chat_server import get_sio_app

# 1) 원래 FastAPI 앱 구성
fastapi_app = FastAPI()
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 업로드 디렉터리 및 정적 서빙 설정
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
fastapi_app.mount("/files", StaticFiles(directory=str(UPLOAD_DIR)), name="files")

# REST 라우터
fastapi_app.include_router(chatbot_router, prefix="")
fastapi_app.include_router(insight_router, prefix="")


@fastapi_app.get("/ping")
def ping():
    return {"pong": True}


@fastapi_app.post("/upload")
async def upload(file: UploadFile = File(...), user: str = Form("익명")):
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

    from app.services.file_service import extract_text_preview

    preview_text = extract_text_preview(save_path, mime=meta["mime"])
    meta["preview"] = preview_text
    return JSONResponse(meta, status_code=200)


# 2) FastAPI를 Socket.IO ASGIApp으로 래핑 → 최종 app
app = get_sio_app(fastapi_app)
