"""Utility helpers to fetch the landing page news cards.

The previous implementation hid most of the intent in helper functions and
returned five generic articles for every guru.  The new version keeps all the
logic in one place so that it reads almost like prose: pick the mentor, build a
clear query, ask Naver for three results, and shape them into a tidy list.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, List

import httpx

NAVER_NEWS_URL = "https://openapi.naver.com/v1/search/news.json"
DEFAULT_NEWS_COUNT = 5

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

# Mentor specific keywords.  Keeping the mapping next to the fetcher makes it
# trivial to tweak the behaviour without searching through multiple functions.
GURU_KEYWORDS: Dict[str, str] = {
    "buffett": "가치투자 대형주 장기 보유",
    "lynch": "성장주 소비재",
    "wood": "혁신 기술 성장주",
}


logger = logging.getLogger(__name__)


def _fallback_for(guru_id: str) -> List[Dict[str, str]]:
    fallback = FALLBACK_NEWS.get(guru_id, FALLBACK_NEWS["buffett"])
    return [dict(item) for item in fallback]


def _naver_headers() -> Dict[str, str]:
    """Return the HTTP headers required by the OpenAPI."""

    headers = {
        "X-Naver-Client-Id": os.getenv("NAVER_CLIENT_ID", ""),
        "X-Naver-Client-Secret": os.getenv("NAVER_CLIENT_SECRET", ""),
        "Accept": "application/json",
        # Some users reported that the OpenAPI occasionally rejects requests
        # without a User-Agent header.  Providing a short identifier keeps the
        # call simple while avoiding the silent 403 responses.
        "User-Agent": "mentor-ai/1.0",  # pragma: allowlist secret
    }
    return headers



def _build_query(guru_id: str) -> str:
    """Compose a simple and readable query string for each mentor.
    
    Note: 네이버 검색 API는 괄호나 복잡한 OR 조건에서 결과가 없을 수 있습니다.
    따라서 단순한 키워드 조합을 사용합니다.
    """

    guru_key = guru_id.lower()
    specific = GURU_KEYWORDS.get(guru_key, "한국 증시 주요 이슈")
    # 괄호 없이 단순한 키워드 조합 사용
    # "주식 증시"를 추가하여 주식 관련 뉴스에 집중
    return f"{specific} 최신 주식 증시"


async def summarize_news(guru_id: str, size: int = DEFAULT_NEWS_COUNT) -> List[Dict[str, str]]:
    """Fetch up to ``size`` news items tailored to the selected mentor.

    The function intentionally stays small: it prepares the headers, sends the
    request, and reshapes the JSON payload into a list of dictionaries that the
    front-end can display without further processing.  When the OpenAPI cannot
    be reached (e.g. missing credentials) it falls back to a short placeholder
    list so the UI still shows a friendly message.
    """

    headers = _naver_headers()
    if not headers["X-Naver-Client-Id"] or not headers["X-Naver-Client-Secret"]:
        logger.warning(
            "NAVER credentials missing; falling back to offline news. "
            "Please check NAVER_CLIENT_ID and NAVER_CLIENT_SECRET environment variables.",
            extra={"guru": guru_id}
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
                extra={"guru": guru_id, "url": NAVER_NEWS_URL}
            )
            response = await client.get(NAVER_NEWS_URL, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            # 응답 구조 확인
            logger.debug(
                "NAVER API response: status=%s, total=%s, items_count=%s",
                response.status_code,
                data.get("total", "N/A"),
                len(data.get("items", [])),
                extra={"guru": guru_id}
            )
            
    except httpx.HTTPStatusError as exc:
            logger.error(
                "NAVER news request failed with status %s: %s",
                exc.response.status_code,
                exc.response.text[:500] if exc.response.text else "No response text",
                extra={"guru": guru_id, "url": NAVER_NEWS_URL, "params": params},
            )
            return _fallback_for(guru_id)
    except Exception as exc:  # pragma: no cover - network/environment specific
            logger.exception(
                "NAVER news request raised an exception: %s",
                str(exc),
                extra={"guru": guru_id, "url": NAVER_NEWS_URL}
            )        
            return _fallback_for(guru_id)

    items = data.get("items") or []
    if not items:
        logger.warning(
            "NAVER API returned empty items list. Response keys: %s, total: %s",
            list(data.keys()),
            data.get("total", "N/A"),
            extra={"guru": guru_id, "query": params["query"], "response_sample": str(data)[:500]}
        )
        return _fallback_for(guru_id)
    
    output: List[Dict[str, str]] = []
    for item in items:
        title = (item.get("title") or "").replace("<b>", "").replace("</b>", "")
        if not title:
            logger.warning("Skipping item with empty title: %s", item)
            continue
        
        # description도 함께 저장 (분석에 사용)
        description = (item.get("description") or "").replace("<b>", "").replace("</b>", "")
        
        output.append(
            {
                "title": title,
                "link": item.get("link", ""),
                "pubDate": item.get("pubDate", ""),
                "source": "naver",
                "description": description,  # 분석에 사용
                "summary": description,  # 호환성을 위해 summary도 추가
            }
        )

    if not output:
        logger.warning(
            "No valid news items after processing. Original items count: %d",
            len(items),
            extra={"guru": guru_id, "items_sample": str(items[:2]) if items else "[]"}
        )
        return _fallback_for(guru_id)

    logger.info(
        "Successfully fetched %d news items for guru: %s",
        len(output),
        guru_id
    )
    return output