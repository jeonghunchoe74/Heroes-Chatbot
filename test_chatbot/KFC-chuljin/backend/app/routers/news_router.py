from fastapi import APIRouter
from app.services.news_service import fetch_latest_news

router = APIRouter()

@router.get("/")
async def get_news():
    return await fetch_latest_news()
