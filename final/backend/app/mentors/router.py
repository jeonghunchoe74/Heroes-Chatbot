# app/mentors/router.py
"""
Intent 라우터 - 사용자 메시지를 RoutedQuery로 변환
"""

from __future__ import annotations

import logging
from typing import List, Optional

from app.mentors.types import Intent, MentorId, RoutedQuery
from app.services.symbol_resolver import resolve_symbols_from_text
from app.utils.mentor_utils import normalize_mentor_id

# intent_service의 detect_intent를 재사용 (중복 제거)
from app.services.intent_service import detect_intent as detect_intent_service

logger = logging.getLogger(__name__)


def route_query(
    user_message: str,
    guru_id: str = "buffett",
    detected_symbols: Optional[List[str]] = None,
) -> RoutedQuery:
    """입력 문장을 Intent, 지역 정보와 함께 RoutedQuery로 변환."""
    mentor_id: MentorId = normalize_mentor_id(guru_id)

    if detected_symbols is None:
        try:
            symbols = resolve_symbols_from_text(user_message)
        except Exception:
            symbols = []
    else:
        symbols = detected_symbols

    lowered = user_message.lower()
    detected_intent = detect_intent_service(user_message)

    intent_map = {
        "smalltalk": Intent.SMALLTALK,
        "news_analysis": Intent.NEWS_ANALYSIS,
        "stock_analysis": Intent.COMPANY_ANALYSIS,
        "stock_comparison": Intent.COMPARE_COMPANIES,
        "stock_metrics": Intent.COMPANY_METRICS,
        "macro_outlook": Intent.MACRO_OUTLOOK,
        "research_analysis": Intent.RESEARCH_ANALYSIS,
    }
    intent = intent_map.get(detected_intent.value, Intent.SMALLTALK)

    def _contains(keywords: List[str]) -> bool:
        return any(kw in lowered for kw in keywords)

    historical_data_keywords = [
        "포트폴리오", "portfolio", "13f", "13-f", "보유", "보유량", "비중",
        "언제 샀", "언제 팔", "매입", "매수", "구매", "들고 있",
    ]
    if _contains(historical_data_keywords):
        intent = Intent.HISTORICAL_DATA
    elif _contains(["과거", "past", "예전", "history", "이전", "옛날"]) and not _contains(
        ["발언", "말했", "말하다", "생각", "관점"]
    ):
        intent = Intent.HISTORICAL_DATA

    macro_hint_keywords = [
        "경제지표", "기준금리", "물가", "인플레이션", "inflation",
        "경기", "경기지표", "환율", "gdp", "cpi", "경제 상황",
    ]
    macro_requested = False
    if intent != Intent.HISTORICAL_DATA and _contains(macro_hint_keywords):
        intent = Intent.MACRO_OUTLOOK
        macro_requested = True

    macro_region_map = {
        "KR": ["한국", "대한민국", "국내", "kr", "korea"],
        "US": ["미국", "us", "usa", "연준", "fed", "월가", "s&p", "nasdaq"],
    }
    macro_regions = [region for region, keywords in macro_region_map.items() if _contains(keywords)]

    # 주가/지표 키워드 확인 (philosophy 분류 전에 체크)
    metric_keywords = ["현재가", "주가", "시총", "per", "pbr", "roe", "eps", "배당", "52주", "가격", "시세"]
    has_metric_keywords = _contains(metric_keywords)
    
    philosophy_keywords = [
        "철학", "원칙", "사상", "주주서한", "책", "인터뷰", "발언", "말했",
        "생각", "관점", "의견", "주장", "강연", "요약", "토론", "안전마진",
        "인플레이션", "inflation", "물가",
    ]
    # "알려줘", "알려"는 주가/지표 키워드가 없을 때만 philosophy로 분류
    rag_philosophy_keywords = ["rag에서", "rag로", "rag기반", "근거로", "찾아줘", "찾아", "알려줘", "알려"]
    mentor_names = ["버핏", "buffett", "워렌", "린치", "lynch", "피터", "우드", "wood", "캐시", "cathie"]
    has_mentor_name = _contains(mentor_names)

    contains_philosophy_kw = _contains(philosophy_keywords)
    contains_rag_kw = _contains(rag_philosophy_keywords)
    
    # 주가/지표 질문은 우선적으로 처리 (philosophy로 바뀌기 전에)
    analysis_keywords = ["전망", "어때", "어떤가", "분석", "관점"]
    if symbols and has_metric_keywords and not _contains(analysis_keywords):
        intent = Intent.COMPANY_METRICS
    
    # COMPANY_METRICS가 이미 설정되었으면 philosophy로 바꾸지 않음
    # region은 아직 정의되지 않았으므로 None으로 설정
    if intent == Intent.COMPANY_METRICS:
        return RoutedQuery(
            intent=intent,
            mentor_id=mentor_id,
            symbols=symbols,
            region=None,
            query_text=user_message,
            macro_regions=None,
        )

    # 주가/지표 키워드가 있으면 "알려줘"를 무시 (철학 질문이 아님)
    if intent != Intent.HISTORICAL_DATA and not macro_requested and not has_metric_keywords:
        if contains_rag_kw:
            intent = Intent.PHILOSOPHY
        elif has_mentor_name and contains_philosophy_kw:
            intent = Intent.PHILOSOPHY

    mentor_economic_keywords = [
        "경제 관점", "경제 생각", "경제 의견", "경제 주장",
        "시장 관점", "시장 생각", "시장 의견", "시장 주장",
        "경제 전망", "경제 예측", "경제 분석", "경기 전망",
        "인플레이션", "inflation", "물가", "금리",
    ]
    if intent not in (Intent.PHILOSOPHY, Intent.HISTORICAL_DATA, Intent.MACRO_OUTLOOK) and has_mentor_name and _contains(
        mentor_economic_keywords
    ):
        intent = Intent.PHILOSOPHY

    comparison_keywords = ["비교", "vs", "대비", "차이", "vs.", "혹은", "중에"]
    if _contains(comparison_keywords) and len(symbols) >= 2:
        intent = Intent.COMPARE_COMPANIES

    if intent == Intent.COMPANY_ANALYSIS:
        if symbols and _contains(metric_keywords) and not _contains(analysis_keywords):
            intent = Intent.COMPANY_METRICS

    region = None
    if intent == Intent.MACRO_OUTLOOK:
        if not macro_regions:
            macro_regions = ["KR"]
        region = macro_regions[0]

    return RoutedQuery(
        intent=intent,
        mentor_id=mentor_id,
        symbols=symbols,
        region=region,
        query_text=user_message,
        macro_regions=macro_regions or None,
    )

