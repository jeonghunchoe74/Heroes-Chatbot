import httpx
from app.core.config import settings

async def get_latest_news(category="business", country="us"):
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{settings.BASE_NEWS_URL}",
            params={"category": category, "country": country, "apiKey": settings.NEWS_API_KEY}
        )
        data = r.json()
        return data.get("articles", [])[:5]

