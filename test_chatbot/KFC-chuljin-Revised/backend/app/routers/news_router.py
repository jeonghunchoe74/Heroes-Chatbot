from fastapi import APIRouter
from app.services.news_service import summarize_news

router = APIRouter(prefix="/news", tags=["News"])

@router.get("/{guru_id}")
async def get_news(guru_id: str):
    """대가 이름별 뉴스 요약 API"""
    data = summarize_news(guru_id)
    return {"news": data}
