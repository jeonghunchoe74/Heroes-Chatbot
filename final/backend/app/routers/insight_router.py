from fastapi import APIRouter
from app.services.insight_service import generate_insight

router = APIRouter()

@router.post("/")
async def get_insight(payload: dict):
    guru = payload.get("guru", "buffett")
    news_text = payload.get("text", "")
    insight = await generate_insight(guru, news_text)
    return {"insight": insight}
