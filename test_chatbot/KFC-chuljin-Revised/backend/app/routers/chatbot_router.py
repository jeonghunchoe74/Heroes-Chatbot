# app/routers/chatbot_router.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.chatbot_service import generate_response, reset_session, get_initial_message

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])

# 🧾 요청/응답 모델 정의
class ChatRequest(BaseModel):
    message: str
    guru_id: Optional[str] = "buffett"  # ✅ 기본값 버핏
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str

@router.get("/init/{guru_id}")
async def chatbot_init(guru_id: str):
    """
    챗봇 초기 진입 시 — 대가 철학 + 관련 뉴스 3건 반환
    """
    try:
        init_data = await get_initial_message(guru_id)
        return init_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze")
async def analyze_article(data: dict):
    """
    특정 뉴스 기사에 대해 대가가 분석 발언
    """
    content = data.get("content") or data.get("summary", "")
    guru_id = data.get("guru_id", "buffet")
    question = f"""
            이 뉴스 기사에 대해 {guru_id}로서 투자 관점에서 간단히 분석해줘.
            무조건적으로 이 뉴스가 관련된 섹터를 "반도체", "유틸리티", "금융서비스", "소프트웨어·서비스", "에너지", "소재",
            "자동차·부품", "통신서비스", "보험", "은행", "헬스케어 장비·서비스" 중 하나로 명시해줘.
            {content}
        """
    ai_response, _ = await generate_response(question, None, guru_id)
    return {"analysis": ai_response}



# 💬 GPT 대화 요청
@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint — guru_id에 따라 각 투자 대가의 철학 + 포트폴리오 기반 응답 생성
    """
    try:
        ai_response, session_id = await generate_response(
            user_input=request.message,
            session_id=request.session_id,
            guru_id=request.guru_id,  # ✅ guru_id 전달
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
