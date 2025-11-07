import asyncio
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import chatbot_router, insight_router
import uvicorn

from app.routers import test_router, news_router, insight_router
from app.sockets.chat_server import sio_app

app = FastAPI(title="Investment Mentor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(test_router.router, prefix="/api/test", tags=["Test"])
app.include_router(news_router.router, prefix="/api/news", tags=["News"])
app.include_router(chatbot_router.router)
app.include_router(insight_router.router, prefix="/api/insight", tags=["Insight"])

app.mount("/ws", sio_app)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

# ---------- Root ----------
@app.get("/")
async def root():
    return {"message": "API 서버가 실행 중입니다."}