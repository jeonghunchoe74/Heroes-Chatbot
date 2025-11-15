# app/mentors/types.py
"""
멘토 에이전트에서 사용하는 데이터 타입 정의
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Literal, Optional

MentorId = Literal["buffett", "lynch", "wood"]


class Intent(str, Enum):
    """사용자 의도 분류"""
    SMALLTALK = "smalltalk"  # 인사, 자기소개
    COMPANY_METRICS = "company_metrics"  # 단순 지표/현재가
    COMPANY_ANALYSIS = "company_analysis"  # 종목 분석 + 해석 (현재 시점)
    COMPARE_COMPANIES = "compare_companies"  # 종목 비교
    MACRO_OUTLOOK = "macro_outlook"  # 시황/매크로 분석
    PHILOSOPHY = "philosophy"  # 철학/주주서한/책 질문
    NEWS_ANALYSIS = "news_analysis"  # 뉴스 분석
    RESEARCH_ANALYSIS = "research_analysis"  # 리포트/리서치 분석
    HISTORICAL_DATA = "historical_data"  # 과거 데이터 조회 (포트폴리오, 과거 발언, 13F 등)


@dataclass
class StockMetrics:
    """종목 지표 데이터"""
    symbol: str
    price: Optional[float] = None
    market_cap: Optional[float] = None
    pe: Optional[float] = None  # PER
    pb: Optional[float] = None  # PBR
    eps: Optional[float] = None
    bps: Optional[float] = None
    roe: Optional[float] = None
    div_yield: Optional[float] = None
    volume: Optional[float] = None
    trade_value: Optional[float] = None
    high_52w: Optional[float] = None
    low_52w: Optional[float] = None


@dataclass
class MacroSnapshot:
    """매크로 레짐 스냅샷"""
    region: str  # "KR" or "US"
    period: Optional[str] = None
    base_rate: Optional[float] = None  # 기준금리
    cpi_yoy: Optional[float] = None  # 물가상승률
    gdp_growth: Optional[float] = None
    fx_krw_usd: Optional[float] = None  # 환율
    unemployment: Optional[float] = None


@dataclass
class NewsItem:
    """뉴스 아이템"""
    symbol: Optional[str] = None
    title: str = ""
    summary: str = ""
    source: str = ""
    published_at: Optional[str] = None


@dataclass
class RoutedQuery:
    """라우터 결과"""
    intent: Intent
    mentor_id: MentorId
    symbols: List[str]
    region: Optional[str] = None  # "KR" or "US"
    query_text: str = ""  # 원본 질문
    macro_regions: Optional[List[str]] = None

