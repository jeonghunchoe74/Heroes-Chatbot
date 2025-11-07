from app.core.news_client import get_latest_news

async def fetch_latest_news():
    articles = await get_latest_news()
    return [{"title": a["title"], "description": a["description"], "url": a["url"]} for a in articles]
