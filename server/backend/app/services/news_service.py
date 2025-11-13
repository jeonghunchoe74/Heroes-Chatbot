# app/services/news_service.py
import time, html
from typing import List, Dict
from openai import OpenAI
from app.services.naver_news import collect_news
from app.services.preprocess import dedup_by_title_host, clean_text
from app.config import MAX_PAGES, NEWS_PER_PAGE, OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

GURU_NEWS_QUERY = {
    "buffett": "유틸리티 OR 금융서비스 OR 소재",  # 🌎 워렌 버핏    
    "lynch": "자동차·부품 OR 헬스케어 장비·서비스 OR 소프트웨어·서비스",  # 🏪 피터 린치
    "wood": "반도체 OR 에너지 OR 통신서비스",  # 💻 캐시 우드
}


def summarize_news(guru_name: str) -> List[Dict]:
    """
    네이버 뉴스 수집 후 상위 3개 요약
    """
    query = GURU_NEWS_QUERY.get(guru_name.lower(), f"{guru_name} 투자 OR 시장")
    items = collect_news(query, max_pages=1, per_page=NEWS_PER_PAGE)
    items = dedup_by_title_host(items)[:3]  # 상위 3개만

    results = []
    for it in items:
        title = clean_text(it["title"])
        desc = clean_text(it.get("description", ""))
        link = it["link"]

        # OpenAI로 요약 생성
        try:
            resp = client.responses.create(
                model="gpt-4o-mini",
                input=f"뉴스 제목: {title}\n내용 요약(한 줄): {desc}\n한 문장으로 간결하게 한국어로 요약해줘.",
                temperature=0.3,
            )
            summary = resp.output_text.strip()
        except Exception:
            summary = desc[:100] + "..."

        results.append({
            "title": title,
            "summary": summary,
            "url": link
        })
        time.sleep(0.3)
    return results
