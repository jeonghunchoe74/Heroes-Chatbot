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

import html
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Set, Tuple

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

# Mentor specific keywords - 멘토별 특성에 맞춘 차별화된 키워드 세트
# 각 멘토마다 여러 검색 쿼리를 시도하여 더 풍부한 결과 확보
GURU_KEYWORDS: Dict[str, List[str]] = {
    "buffett": [
        # 대형주, 가치주 중심
        "대형주 가치투자 배당",
        "삼성전자 SK하이닉스 현대차 재무 건전성",
        "코스피 대형주 밸류에이션",
        "배당수익률 높은 주식",
        "ROE 높은 기업 경쟁우위",
    ],
    "lynch": [
        # 소비재, 성장주 중심 (검색 가능한 일반 키워드로 변경)
        "소비재 주식",
        "성장주",
        "유통 식품주",
        "중소형주",
        "개인투자 관심주",
    ],
    "wood": [
        # 혁신 기술 중심 (검색 가능한 일반 키워드로 변경)
        "AI 인공지능",
        "반도체",
        "바이오테크",
        "전기차",
        "블록체인",
        "기술주",
    ],
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


def _build_queries(guru_id: str) -> List[str]:
    """멘토별 검색 키워드 리스트 반환 (여러 쿼리로 검색하여 결과 확보)"""
    guru_key = guru_id.lower()
    keywords_list = GURU_KEYWORDS.get(guru_key, ["한국 증시 주요 이슈"])
    # 각 키워드에 최신성 강조를 추가
    return [f"{kw} 주식 증시" for kw in keywords_list]


def _is_recent_news(pub_date_str: str, days: int = 3) -> bool:
    """뉴스가 최근 N일 이내인지 확인"""
    if not pub_date_str:
        return True  # 날짜 정보가 없으면 포함
    
    try:
        # Naver API 날짜 형식: "Mon, 01 Jan 2024 12:00:00 +0900"
        # 또는 "20240101" 형식도 가능
        pub_date_str = pub_date_str.strip()
        
        # 다양한 날짜 형식 파싱 시도
        date_formats = [
            "%a, %d %b %Y %H:%M:%S %z",
            "%Y%m%d",
            "%Y-%m-%d",
            "%Y.%m.%d",
        ]
        
        pub_date = None
        for fmt in date_formats:
            try:
                if fmt.endswith("%z"):
                    pub_date = datetime.strptime(pub_date_str, fmt)
                else:
                    pub_date = datetime.strptime(pub_date_str[:10], fmt)
                break
            except ValueError:
                continue
        
        if pub_date is None:
            return True  # 파싱 실패시 포함
        
        # 시간대 정보가 없으면 현재 시간대 기준으로 처리
        if pub_date.tzinfo is None:
            pub_date = pub_date.replace(tzinfo=datetime.now().astimezone().tzinfo)
        
        cutoff = datetime.now(pub_date.tzinfo) - timedelta(days=days)
        return pub_date >= cutoff
    except Exception:
        logger.debug(f"날짜 파싱 실패: {pub_date_str}, 포함 처리")
        return True  # 파싱 실패시 포함


def _score_relevance(item: Dict, guru_id: str) -> float:
    """뉴스 아이템이 멘토 특성에 얼마나 관련있는지 점수 계산 (0.0 ~ 1.0)"""
    title = (item.get("title") or "").lower()
    description = (item.get("description") or "").lower()
    text = f"{title} {description}"
    
    guru_key = guru_id.lower()
    
    # 멘토별 관련 키워드 가중치
    relevance_keywords = {
        "buffett": {
            "대형주": 0.3,
            "가치": 0.3,
            "배당": 0.2,
            "삼성": 0.15,
            "SK하이닉스": 0.15,
            "현대차": 0.15,
            "ROE": 0.2,
            "재무": 0.15,
            "경쟁우위": 0.15,
            "모닝스타": 0.1,
        },
        "lynch": {
            "성장": 0.3,
            "소비": 0.3,
            "PEG": 0.2,
            "EPS": 0.2,
            "중소형": 0.15,
            "유통": 0.15,
            "식품": 0.15,
            "트렌드": 0.1,
            "개인투자": 0.1,
        },
        "wood": {
            "AI": 0.25,
            "인공지능": 0.25,
            "반도체": 0.2,
            "바이오": 0.15,
            "전기차": 0.15,
            "배터리": 0.15,
            "블록체인": 0.1,
            "메타버스": 0.1,
            "혁신": 0.2,
            "기술": 0.2,
            "테슬라": 0.1,
            "엔비디아": 0.1,
        },
    }
    
    keywords = relevance_keywords.get(guru_key, {})
    score = 0.0
    
    for keyword, weight in keywords.items():
        if keyword in text:
            score += weight
    
    # 최신성 보너스 (최근 1일 이내면 추가 점수)
    pub_date = item.get("pubDate", "")
    if _is_recent_news(pub_date, days=1):
        score += 0.1
    
    return min(score, 1.0)  # 최대 1.0으로 제한


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

    # 여러 쿼리로 검색하여 더 많은 결과 확보
    # 각 쿼리에서 최고 기사 1개씩 선택하여 다양성 확보
    queries = _build_queries(guru_id)
    query_results: List[List[Dict]] = []  # 쿼리별 결과 저장
    seen_titles: Set[str] = set()  # 중복 제거용

    # 최소 size개 이상의 기사를 확보하기 위해 충분한 쿼리 시도 (최소 5개)
    max_queries = max(size * 2, 5)

    async with httpx.AsyncClient(timeout=10.0) as client:
        for query in queries[:max_queries]:  # 충분한 쿼리 시도
            try:
                params = {
                    "query": query,
                    "display": "10",  # 각 쿼리당 더 많이 가져와서 필터링
                    "sort": "date",  # 최신순 정렬
                }

                logger.info(
                    "Requesting NAVER news API: query=%s, display=%s",
                    query,
                    params["display"],
                    extra={"guru": guru_id},
                )

                response = await client.get(NAVER_NEWS_URL, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                items = data.get("items") or []
                query_items: List[Dict] = []
                
                # 중복 제거 및 최신성 필터링
                for item in items:
                    title = (item.get("title") or "").strip()
                    if not title:
                        continue
                    
                    # 중복 제거
                    title_key = title.lower()
                    if title_key in seen_titles:
                        continue
                    seen_titles.add(title_key)
                    
                    # 최근 7일 이내 뉴스만 포함 (너무 오래된 뉴스 제외)
                    pub_date = item.get("pubDate", "")
                    if not _is_recent_news(pub_date, days=7):
                        continue
                    
                    query_items.append(item)

                if query_items:
                    query_results.append(query_items)
                    logger.debug(
                        "NAVER API response for query '%s': total=%s, items_count=%s, valid_items=%s",
                        query,
                        data.get("total", "N/A"),
                        len(items),
                        len(query_items),
                        extra={"guru": guru_id},
                    )

            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "NAVER news request failed for query '%s' with status %s: %s",
                    query,
                    exc.response.status_code,
                    exc.response.text[:200] if exc.response.text else "No response text",
                    extra={"guru": guru_id},
                )
                continue  # 다음 쿼리 시도
            except Exception as exc:
                logger.warning(
                    "NAVER news request raised an exception for query '%s': %s",
                    query,
                    str(exc),
                    extra={"guru": guru_id},
                )
                continue  # 다음 쿼리 시도

    if not query_results:
        logger.warning(
            "No news items found after all queries. Tried queries: %s",
            queries,
            extra={"guru": guru_id},
        )
        return _fallback_for(guru_id)

    # 날짜 파싱 헬퍼 함수 (내부 정의)
    def _get_date_for_sort_helper(item: Dict) -> datetime:
        """날짜 파싱 헬퍼 함수"""
        pub_date = item.get("pubDate", "")
        if not pub_date:
            return datetime.min
        try:
            for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%Y%m%d", "%Y-%m-%d"]:
                try:
                    if fmt.endswith("%z"):
                        return datetime.strptime(pub_date, fmt)
                    return datetime.strptime(pub_date[:10], fmt)
                except ValueError:
                    continue
        except Exception:
            pass
        return datetime.min
    
    # 각 쿼리에서 최고 점수 기사 1개씩 선택 (다양성 확보)
    selected_items: List[tuple] = []  # (item, score, query_index) 튜플
    for query_idx, query_items in enumerate(query_results):
        if not query_items:
            continue
        
        # 관련성 점수 계산 및 정렬
        scored = [(item, _score_relevance(item, guru_id)) for item in query_items]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # 최고 점수 기사 선택
        best_item, best_score = scored[0]
        selected_items.append((best_item, best_score, query_idx))
        
        logger.debug(
            "Selected best item from query %d: score=%.2f, title=%s",
            query_idx,
            best_score,
            (best_item.get("title") or "")[:50],
            extra={"guru": guru_id},
        )
    
    # 최종적으로 관련성 점수와 최신성 기준으로 정렬
    selected_items.sort(key=lambda x: (x[1], _get_date_for_sort_helper(x[0])), reverse=True)
    
    # 다양성 유지하면서 최소 size개 확보
    items: List[Dict] = []
    used_query_indices: Set[int] = set()
    used_titles: Set[str] = set()  # 제목 기반 중복 체크
    used_links: Set[str] = set()  # 링크 기반 중복 체크
    
    def _normalize_title(title: str) -> str:
        """제목 정규화 (공백 제거, 소문자 변환)"""
        return "".join(title.lower().split())
    
    def _is_similar_title(title1: str, title2: str) -> bool:
        """두 제목이 유사한지 체크 (핵심 단어 60% 이상 겹치면 유사)"""
        # 단어 단위로 분리 (한글, 영문, 숫자)
        import re
        words1 = set(re.findall(r'[\w가-힣]+', title1.lower()))
        words2 = set(re.findall(r'[\w가-힣]+', title2.lower()))
        
        if not words1 or not words2:
            return False
        
        # 공통 단어 비율 계산
        common_words = words1 & words2
        total_words = words1 | words2
        
        if not total_words:
            return False
        
        # 공통 단어 비율이 60% 이상이면 유사
        similarity = len(common_words) / len(total_words)
        
        # 또는 공통 단어가 3개 이상이면 유사 (짧은 제목 대응)
        if len(common_words) >= 3:
            return True
        
        return similarity > 0.6  # 60% 이상 유사하면 중복으로 간주
    
    def _is_duplicate(item: Dict) -> bool:
        """제목 및 링크 기반 중복 체크 (강화)"""
        title = (item.get("title") or "").strip()
        link = (item.get("link") or "").strip()
        
        if not title:
            return True
        
        # 링크 기반 중복 체크 (가장 확실)
        if link and link in used_links:
            return True
        
        # 제목 정규화
        normalized_title = _normalize_title(title)
        if normalized_title in used_titles:
            return True
        
        # 유사 제목 체크 (제목이 약간 다르지만 같은 뉴스일 수 있음)
        for used_title in used_titles:
            if _is_similar_title(title, used_title):
                logger.debug(
                    "Similar title detected: '%s' vs '%s'",
                    title[:50],
                    used_title[:50],
                    extra={"guru": guru_id},
                )
                return True
        
        # 중복이 아니면 추가
        used_titles.add(normalized_title)
        if link:
            used_links.add(link)
        return False
    
    # 1단계: 각 쿼리에서 최소 1개씩 선택 (다양성 확보)
    # 쿼리 인덱스별로 그룹화하여 각 쿼리에서 최대 1개씩만 선택
    query_items_by_idx: Dict[int, List[tuple]] = {}  # query_idx -> [(item, score), ...]
    for item, score, query_idx in selected_items:
        if query_idx not in query_items_by_idx:
            query_items_by_idx[query_idx] = []
        query_items_by_idx[query_idx].append((item, score))
    
    # 각 쿼리에서 최고 점수 기사 1개씩 선택 (다양성 확보)
    for query_idx in sorted(query_items_by_idx.keys()):
        if len(items) >= size:
            break
        query_best_items = sorted(query_items_by_idx[query_idx], key=lambda x: x[1], reverse=True)
        for item, score in query_best_items:
            if not _is_duplicate(item):
                items.append(item)
                used_query_indices.add(query_idx)
                break  # 각 쿼리에서 1개만 선택
    
    # 2단계: 부족하면 관련성 점수 상위에서 추가 선택 (다른 쿼리에서)
    if len(items) < size:
        for item, score, query_idx in selected_items:
            if len(items) >= size:
                break
            # 이미 사용한 쿼리 인덱스는 피하고, 중복 체크
            if query_idx not in used_query_indices and not _is_duplicate(item):
                items.append(item)
                used_query_indices.add(query_idx)
    
    # 2-1단계: 여전히 부족하면 이미 사용한 쿼리에서도 추가 선택 (엄격한 중복 체크)
    if len(items) < size:
        for item, score, query_idx in selected_items:
            if len(items) >= size:
                break
            if not _is_duplicate(item):  # 엄격한 중복 체크만 통과하면 추가
                items.append(item)
    
    # 3단계: 여전히 부족하면 모든 쿼리 결과를 합쳐서 상위에서 선택
    if len(items) < size:
        all_scored_items: List[tuple] = []
        for query_items in query_results:
            for item in query_items:
                if not _is_duplicate(item):  # 중복 체크
                    score = _score_relevance(item, guru_id)
                    all_scored_items.append((item, score))
        
        all_scored_items.sort(key=lambda x: (x[1], _get_date_for_sort_helper(x[0])), reverse=True)
        
        for item, score in all_scored_items:
            if len(items) >= size:
                break
            if not _is_duplicate(item):  # 중복 제거
                items.append(item)
    
    # 4단계: 최종적으로도 부족하면 최근 14일로 확장하여 추가 검색
    if len(items) < size:
        logger.warning(
            "Still need %d more items, trying to extend date range",
            size - len(items),
            extra={"guru": guru_id},
        )
        # 최근 14일로 확장하여 다시 검색 (간단한 쿼리로)
        try:
            simple_query = GURU_KEYWORDS.get(guru_id.lower(), ["주식"])[0] + " 주식 증시"
            params = {
                "query": simple_query,
                "display": str((size - len(items)) * 3),  # 부족한 개수의 3배
                "sort": "date",
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(NAVER_NEWS_URL, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                extra_items = data.get("items") or []
                
                for item in extra_items:
                    if len(items) >= size:
                        break
                    title = (item.get("title") or "").strip()
                    if not title or _is_duplicate({"title": title}):
                        continue
                    # 최근 14일 이내면 포함
                    pub_date = item.get("pubDate", "")
                    if _is_recent_news(pub_date, days=14):
                        items.append(item)
        except Exception as exc:
            logger.warning("Failed to fetch additional items: %s", exc, extra={"guru": guru_id})
    
    # 최종적으로도 부족하면 fallback으로 보완
    if len(items) < size:
        fallback_items = _fallback_for(guru_id)
        needed = size - len(items)
        # fallback에서 필요한 만큼만 추가 (중복 체크)
        for fallback_item in fallback_items:
            if len(items) >= size:
                break
            fallback_title = (fallback_item.get("title") or "").strip().lower()
            if fallback_title not in used_titles:
                items.append(fallback_item)
                used_titles.add(fallback_title)
    
    logger.info(
        "Collected %d unique news items from %d queries, selected %d diverse items (target: %d)",
        sum(len(qr) for qr in query_results),
        len(query_results),
        len(items),
        size,
        extra={"guru": guru_id},
    )

    # 최종 결과 생성 및 추가 필터링 (최종 중복 체크)
    output: List[Dict[str, str]] = []
    final_used_titles: Set[str] = set()
    final_used_links: Set[str] = set()
    
    for item in items[:size * 2]:  # 여유있게 가져와서 최종 필터링
        title = (item.get("title") or "").replace("<b>", "").replace("</b>", "")
        # HTML 엔티티 디코딩 (&quot; -> ", &amp; -> & 등)
        title = html.unescape(title)
        if not title:
            continue

        link = (item.get("link") or "").strip()
        normalized_title = _normalize_title(title)
        
        # 최종 중복 체크 (링크와 제목 모두 확인)
        if link and link in final_used_links:
            continue
        if normalized_title in final_used_titles:
            continue
        
        # 유사 제목 체크
        is_duplicate = False
        for used_title in final_used_titles:
            if _is_similar_title(title, used_title):
                is_duplicate = True
                break
        if is_duplicate:
            continue

        description = (item.get("description") or "").replace("<b>", "").replace("</b>", "")
        # HTML 엔티티 디코딩
        description = html.unescape(description)

        pub_date = item.get("pubDate", "")
        
        # 최종적으로 최근 3일 이내 뉴스 우선 (더 최신 뉴스 선호)
        relevance_score = _score_relevance(item, guru_id)
        
        output.append(
            {
                "title": title,
                "link": link,
                "pubDate": pub_date,
                "source": "naver",
                "description": description,
                "summary": description,  # 호환성 유지용
                # 디버깅용 메타데이터 (선택적)
                "_relevance_score": round(relevance_score, 2),
            }
        )
        
        # 사용한 제목과 링크 기록
        final_used_titles.add(normalized_title)
        if link:
            final_used_links.add(link)
        
        if len(output) >= size:
            break

    # 최신성 기준으로 한 번 더 정렬 (같은 관련성 점수면 최신 뉴스 우선)
    output.sort(key=lambda x: _get_date_for_sort_helper(x), reverse=True)
    output = output[:size]  # 최종 개수 제한

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
