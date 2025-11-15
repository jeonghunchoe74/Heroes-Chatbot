from fastapi import APIRouter
from app.services.news_service import summarize_news, fetch_latest_news

# /news 아래에서 두 가지 기능 제공:
# 1) GET /news/           → 전체/공통 최신 뉴스 (fetch_latest_news)
# 2) GET /news/{guru_id}  → 멘토(대가)별 뉴스 요약 (summarize_news)
router = APIRouter(prefix="/news", tags=["News"])


@router.get("/")
async def get_latest_news():
    """
    공통 최신 뉴스 API
    (이전 버전: router = APIRouter(); @router.get("/") → fetch_latest_news())과 동일한 기능
    """
    return await fetch_latest_news()


@router.get("/{guru_id}")
async def get_news_by_guru(guru_id: str):
    """
    대가 이름별 뉴스 요약 API
    (이전 버전: prefix="/news"; @router.get("/{guru_id}") → summarize_news(guru_id))과 동일한 기능
    """
    data = await summarize_news(guru_id)
    return {"news": data}
