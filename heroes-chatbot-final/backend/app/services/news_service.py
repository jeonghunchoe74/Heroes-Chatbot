# app/services/news_service.py
from __future__ import annotations

"""
News helper utilities

- summarize_news(guru_id, size):
    멘토(guru)에 맞춘 키워드로 Naver News API에서 뉴스 가져오기

- fetch_latest_news():
    서비스 공통 '최신 뉴스'용 래퍼
    (기존처럼 app.core.news_client.get_latest_news() 사용)
"""

import logging
import os
from typing import Dict, List

import httpx

try:
    # 예전 버전 호환: 공통 뉴스 클라이언트
    from app.core.news_client import get_latest_news
except ImportError:  # core 모듈이 없는 환경에서도 동작하도록 방어
    get_latest_news = None  # type: ignore

NAVER_NEWS_URL = "https://openapi.naver.com/v1/search/news.json"
DEFAULT_NEWS_COUNT = 3

FALLBACK_NEWS: Dict[str, List[Dict[str, str]]] = {
    "buffett": [
        {
            "title": "실시간 뉴스를 불러오지 못했습니다. 대신 가치 투자 관점의 주요 이슈를 확인해 보세요.",
            "link": "",
            "pubDate": "",
            "source": "offline",
        }
        for _ in range(DEFAULT_NEWS_COUNT)
    ],
    "lynch": [
        {
            "title": "실시간 뉴스를 불러오지 못했습니다. 소비재와 성장주 동향을 다시 시도해 주세요.",
            "link": "",
            "pubDate": "",
            "source": "offline",
        }
        for _ in range(DEFAULT_NEWS_COUNT)
    ],
    "wood": [
        {
            "title": "실시간 뉴스를 불러오지 못했습니다. 혁신 기술 섹터 소식을 다시 요청해 주세요.",
            "link": "",
            "pubDate": "",
            "source": "offline",
        }
        for _ in range(DEFAULT_NEWS_COUNT)
    ],
}

# Mentor specific keywords
GURU_KEYWORDS: Dict[str, str] = {
    "buffett": "워렌 버핏 가치투자 대형주 장기 보유",
    "lynch": "피터 린치 성장주 소비재",
    "wood": "캐시 우드 혁신 기술 성장주",
}

logger = logging.getLogger(__name__)


def _fallback_for(guru_id: str) -> List[Dict[str, str]]:
    """멘토별 기본 fallback 카드 목록 복제"""
    fallback = FALLBACK_NEWS.get(guru_id, FALLBACK_NEWS["buffett"])
    return [dict(item) for item in fallback]


def _naver_headers() -> Dict[str, str]:
    """Naver OpenAPI 호출에 필요한 헤더 구성"""

    headers = {
        "X-Naver-Client-Id": os.getenv("NAVER_CLIENT_ID", ""),
        "X-Naver-Client-Secret": os.getenv("NAVER_CLIENT_SECRET", ""),
        "Accept": "application/json",
        # User-Agent 없으면 간헐적으로 403 나는 케이스 방지
        "User-Agent": "mentor-ai/1.0",  # pragma: allowlist secret
    }
    return headers


def _build_query(guru_id: str) -> str:
    """멘토별 검색 키워드 구성 (단순 키워드 조합 중심)"""

    guru_key = guru_id.lower()
    specific = GURU_KEYWORDS.get(guru_key, "한국 증시 주요 이슈")
    # 괄호/복잡한 OR 조건 피하고, 주식 관련성을 높이기 위해 '주식 증시'를 같이 붙임
    return f"{specific} 주식 증시"


async def summarize_news(guru_id: str, size: int = DEFAULT_NEWS_COUNT) -> List[Dict[str, str]]:
    """
    멘토(guru_id)에 맞춘 뉴스 요약 리스트 반환.

    반환 형식(프론트에서 바로 카드로 사용 가능):
    [
        {
            "title": "...",
            "link": "...",
            "pubDate": "...",
            "source": "naver" | "offline",
            "description": "...",  # 원문 요약/본문
            "summary": "...",      # 호환용 alias
        },
        ...
    ]
    """

    headers = _naver_headers()
    if not headers["X-Naver-Client-Id"] or not headers["X-Naver-Client-Secret"]:
        logger.warning(
            "NAVER credentials missing; falling back to offline news. "
            "Please check NAVER_CLIENT_ID and NAVER_CLIENT_SECRET environment variables.",
            extra={"guru": guru_id},
        )
        return _fallback_for(guru_id)

    params = {
        "query": _build_query(guru_id),
        "display": str(size),
        "sort": "date",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            logger.info(
                "Requesting NAVER news API: query=%s, display=%s",
                params["query"],
                params["display"],
                extra={"guru": guru_id, "url": NAVER_NEWS_URL},
            )
            response = await client.get(NAVER_NEWS_URL, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            logger.debug(
                "NAVER API response: status=%s, total=%s, items_count=%s",
                response.status_code,
                data.get("total", "N/A"),
                len(data.get("items", [])),
                extra={"guru": guru_id},
            )

    except httpx.HTTPStatusError as exc:
        logger.error(
            "NAVER news request failed with status %s: %s",
            exc.response.status_code,
            exc.response.text[:500] if exc.response.text else "No response text",
            extra={"guru": guru_id, "url": NAVER_NEWS_URL, "params": params},
        )
        return _fallback_for(guru_id)
    except Exception as exc:  # pragma: no cover - network/env specific
        logger.exception(
            "NAVER news request raised an exception: %s",
            str(exc),
            extra={"guru": guru_id, "url": NAVER_NEWS_URL},
        )
        return _fallback_for(guru_id)

    items = data.get("items") or []
    if not items:
        logger.warning(
            "NAVER API returned empty items list. Response keys: %s, total: %s",
            list(data.keys()),
            data.get("total", "N/A"),
            extra={"guru": guru_id, "query": params["query"], "response_sample": str(data)[:500]},
        )
        return _fallback_for(guru_id)

    output: List[Dict[str, str]] = []
    for item in items:
        title = (item.get("title") or "").replace("<b>", "").replace("</b>", "")
        if not title:
            logger.warning("Skipping item with empty title: %s", item)
            continue

        description = (item.get("description") or "").replace("<b>", "").replace("</b>", "")

        output.append(
            {
                "title": title,
                "link": item.get("link", ""),
                "pubDate": item.get("pubDate", ""),
                "source": "naver",
                "description": description,
                "summary": description,  # 호환성 유지용
            }
        )

    if not output:
        logger.warning(
            "No valid news items after processing. Original items count: %d",
            len(items),
            extra={"guru": guru_id, "items_sample": str(items[:2]) if items else "[]"},
        )
        return _fallback_for(guru_id)

    logger.info(
        "Successfully fetched %d news items for guru: %s",
        len(output),
        guru_id,
    )
    return output


# ─────────────────────────────
# 예전 버전 호환: fetch_latest_news
#   - /news/ 엔드포인트에서 사용
#   - app.core.news_client.get_latest_news()가 있으면 그걸 사용
#   - 없으면 buffett 기준 summarize_news로 대체
# ─────────────────────────────

async def fetch_latest_news():
    """
    공통 '최신 뉴스' 리스트 반환.

    원래 구현:
        from app.core.news_client import get_latest_news
        articles = await get_latest_news()
        return [{"title": a["title"], "description": a["description"], "url": a["url"]} ...]

    core.news_client가 없거나 에러가 나면
    buffett 기준 summarize_news 결과를 단순 변환해서 돌려준다.
    """

    # 1) core.news_client 가 있는 경우: 기존 동작 유지
    if get_latest_news is not None:
        try:
            articles = await get_latest_news()
            return [
                {
                    "title": a.get("title", ""),
                    "description": a.get("description", ""),
                    "url": a.get("url", ""),
                }
                for a in (articles or [])
            ]
        except Exception as exc:
            logger.error("get_latest_news() failed, falling back to summarize_news: %s", exc)

    # 2) 없거나 실패한 경우: buffett 기준 summarize_news 사용
    buffett_news = await summarize_news("buffett", size=DEFAULT_NEWS_COUNT)
    return [
        {
            "title": n.get("title", ""),
            "description": n.get("description", "") or n.get("summary", ""),
            "url": n.get("link", ""),
        }
        for n in buffett_news
    ]
