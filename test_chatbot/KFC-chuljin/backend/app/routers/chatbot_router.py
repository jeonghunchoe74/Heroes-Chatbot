# app/routers/chatbot_router.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.chatbot_service import generate_response, reset_session

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])

# 요청/응답 모델
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str

# 💬 메시지 전송 (GPT 대화)
@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        ai_response, session_id = await generate_response(
            request.message, request.session_id
        )
        return ChatResponse(response=ai_response, session_id=session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"챗봇 오류: {str(e)}")

# 🔄 세션 초기화
@router.post("/reset")
async def reset(session_id: Optional[str] = None):
    message = reset_session(session_id)
    return {"message": message}

# 📊 예시 차트 데이터 (옵션)
@router.get("/chart")
async def get_chart_data():
    chart_data = [
        {"name": "Python", "value": 30},
        {"name": "JavaScript", "value": 25},
        {"name": "Java", "value": 20},
        {"name": "C++", "value": 15},
        {"name": "기타", "value": 10},
    ]
    return {"data": chart_data}

# ❤️ 헬스체크 (옵션)
@router.get("/health")
async def health_check():
    return {"status": "healthy"}
