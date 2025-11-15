# app/services/intent_service.py
"""
Intent 서비스 - 사용자 입력에서 intent, 심볼, region 등을 추론

역할:
- Intent 분류: smalltalk, news_analysis, stock_analysis, stock_comparison, stock_metrics, macro_outlook, research_analysis
- 심볼 추출: 국내 종목명/티커 추출
- Region 감지: KR, US 등
- Metric 키워드 추출: PER, PBR 등
"""

from __future__ import annotations

import logging
import re
from enum import Enum
from typing import List, Optional, Set

from app.services.symbol_resolver import resolve_symbols_from_text

logger = logging.getLogger(__name__)


class Intent(str, Enum):
    """사용자 의도 분류"""
    SMALLTALK = "smalltalk"  # 인사, 자기소개
    NEWS_ANALYSIS = "news_analysis"  # 뉴스 분석
    STOCK_ANALYSIS = "stock_analysis"  # 단일 종목 분석
    STOCK_COMPARISON = "stock_comparison"  # 종목 비교
    STOCK_METRICS = "stock_metrics"  # 단순 지표 질문 (PER, PBR 등)
    MACRO_OUTLOOK = "macro_outlook"  # 시황/매크로 분석
    RESEARCH_ANALYSIS = "research_analysis"  # 리포트/리서치 분석


# Metric 키워드 매핑
METRIC_KEYWORDS: dict[str, set[str]] = {
    "per": {"PER"},
    "pbr": {"PBR"},
    "eps": {"EPS"},
    "bps": {"BPS"},
    "배당": {"DIV_YIELD"},
    "배당수익률": {"DIV_YIELD"},
    "시가총액": {"MKT_CAP"},
    "시총": {"MKT_CAP"},
    "현재가": {"CUR"},
    "주가": {"CUR"},
    "52주 최고": {"52W_H"},
    "52주 최저": {"52W_L"},
    "52주": {"52W_H", "52W_L"},
    "거래량": {"VOL"},
    "거래대금": {"TRADE_VALUE"},
    "roe": {"ROE"},
    "영업이익": {"OP_INCOME"},
    "순이익": {"NET_INCOME"},
    "매출": {"SALES"},
    "매출액": {"SALES"},
    "실적": {"SALES", "OP_INCOME", "NET_INCOME"},
    "고가": {"HIGH"},
    "저가": {"LOW"},
    "시초가": {"OPEN"},
    "전일종가": {"PREV_CLOSE"},
}

# Intent 감지 키워드
SMALLTALK_KEYWORDS = ["안녕", "누구", "소개", "이름", "hello", "hi", "who are you", "who are"]
NEWS_KEYWORDS = ["뉴스", "정책", "headline", "news", "다음 뉴스", "뉴스 내용", "뉴스 분석", "분석해줘", "분석해"]
STOCK_KEYWORDS = ["회사", "종목", "티커", "코드", "005", "000", "현재가", "주가", "시세", "가격"]
COMPARISON_KEYWORDS = ["비교", "vs", "대비", "차이", "랑", "와", "하고"]
MACRO_KEYWORDS = ["시황", "경기", "매크로", "금리", "inflation", "recession", "경제", "경제지표", "기준금리", "물가", "환율"]
RESEARCH_KEYWORDS = ["리포트", "리서치", "보고서", "애널리스트"]
METRIC_KEYWORDS_LIST = ["per", "pbr", "eps", "bps", "roe", "배당", "배당수익률", "시가총액", "시총", "52주", "거래량", "거래대금", "실적"]


def detect_intent(message: str) -> Intent:
    """
    사용자 메시지에서 intent를 추론.
    
    우선순위:
    1. smalltalk (인사)
    2. macro_outlook (매크로)
    3. stock_comparison (비교)
    4. stock_metrics (단순 지표)
    5. stock_analysis (종목 분석)
    6. news_analysis (뉴스)
    7. research_analysis (리서치)
    """
    if not message:
        return Intent.SMALLTALK
    
    lowered = message.lower()
    
    # 1. Smalltalk
    if any(kw in lowered for kw in SMALLTALK_KEYWORDS):
        return Intent.SMALLTALK
    
    # 2. Macro outlook
    if any(kw in lowered for kw in MACRO_KEYWORDS):
        return Intent.MACRO_OUTLOOK
    
    # 3. Research analysis
    if any(kw in lowered for kw in RESEARCH_KEYWORDS):
        return Intent.RESEARCH_ANALYSIS
    
    # 4. News analysis
    if any(kw in lowered for kw in NEWS_KEYWORDS):
        return Intent.NEWS_ANALYSIS
    
    # 5. Stock comparison
    if any(kw in lowered for kw in COMPARISON_KEYWORDS):
        return Intent.STOCK_COMPARISON
    
    # 6. Stock metrics (단순 지표 질문)
    if any(kw in lowered for kw in METRIC_KEYWORDS_LIST):
        # 종목명이 있으면 stock_metrics, 없으면 stock_analysis로 분류
        symbols = extract_symbols(message)
        if symbols:
            return Intent.STOCK_METRICS
    
    # 7. Stock analysis (종목 관련)
    if any(kw in lowered for kw in STOCK_KEYWORDS):
        return Intent.STOCK_ANALYSIS
    
    # 기본값: smalltalk
    return Intent.SMALLTALK


def extract_symbols(message: str) -> List[str]:
    """
    사용자 메시지에서 종목명/티커를 추출.
    
    기존 symbol_resolver를 사용하되, 실패 시 fallback 로직 포함.
    """
    if not message:
        return []
    
    try:
        symbols = resolve_symbols_from_text(message)
        if symbols:
            return symbols
    except Exception as exc:
        logger.debug(f"Symbol extraction failed: {exc}")
    
    # Fallback: 6자리 숫자 패턴 (티커)
    code_pattern = re.compile(r"\b\d{6}\b")
    codes = code_pattern.findall(message)
    if codes:
        return codes
    
    return []


def detect_region_or_market(message: str) -> Optional[str]:
    """
    사용자 메시지에서 지역/시장을 감지.
    
    Returns:
        "KR", "US", 또는 None
    """
    if not message:
        return None
    
    lowered = message.lower()
    
    # 미국 키워드
    us_keywords = ["미국", "us", "united states", "fed", "federal reserve", "연준", "s&p", "nasdaq", "dow"]
    if any(kw in lowered for kw in us_keywords):
        return "US"
    
    # 한국 키워드 (명시적)
    kr_keywords = ["한국", "korea", "kr", "코스피", "코스닥", "한국은행", "한은"]
    if any(kw in lowered for kw in kr_keywords):
        return "KR"
    
    # 기본값: None (추론 불가)
    return None


def extract_requested_metrics(message: str) -> Set[str]:
    """
    사용자 메시지에서 요청된 지표를 추출.
    
    Returns:
        Kiwoom API 필드명 세트 (예: {"PER", "PBR", "CUR"})
    """
    if not message:
        return set()
    
    lowered = message.lower()
    requested = set()
    
    for keyword, metric_set in METRIC_KEYWORDS.items():
        if keyword in lowered:
            requested.update(metric_set)
    
    return requested


def extract_topic_keywords(message: str) -> List[str]:
    """
    사용자 메시지에서 주제 키워드를 추출 (RAG 필터링용).
    
    Returns:
        주제 키워드 리스트 (예: ["성장", "밸류에이션", "배당"])
    """
    if not message:
        return []
    
    # 간단한 키워드 추출 (향후 개선 가능)
    topic_keywords = [
        "성장", "growth", "밸류에이션", "valuation", "배당", "dividend",
        "수익성", "profitability", "안전마진", "margin of safety",
        "모멘텀", "momentum", "사이클", "cycle", "인플레이션", "inflation",
        "금리", "interest rate", "환율", "exchange rate"
    ]
    
    lowered = message.lower()
    found = [kw for kw in topic_keywords if kw in lowered]
    
    return found

