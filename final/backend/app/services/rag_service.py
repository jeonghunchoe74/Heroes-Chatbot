# app/services/rag_service.py
"""
RAG 서비스 - 새로운 JSONL 파일들 통합 및 캐시 구조

새로운 RAG 코퍼스:
- guru_philosophy_*.jsonl: 멘토 철학/원문
- guru_portfolio_with_macro.jsonl: 미국 멘토들의 13F + 미국 매크로 히스토리
- kr_macro_quarterly.jsonl: 한국 분기별 매크로 레짐 스냅샷

리팩터링: 초기 로딩 캐시 구조 + Intent 기반 필터링
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import csv
from typing import Any, Dict, List, Optional, Set

from app.mentors.types import Intent
from app.utils.mentor_utils import MentorId, normalize_mentor_id

logger = logging.getLogger(__name__)

# 데이터 경로 설정
import os
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "app" / "data"

# RAG 데이터 경로 우선순위:
# 1. 환경변수 RAG_DATA_DIR
# 2. rebuild 폴더 (개발용)
# 3. app/data/philosophy, app/data/ (기본)
RAG_DATA_DIR = os.getenv("RAG_DATA_DIR")
if RAG_DATA_DIR:
    RAG_BASE = Path(RAG_DATA_DIR)
else:
    # rebuild 폴더 확인 (개발용)
    REBUILD_DIR = Path(r"C:\Users\edukd\OneDrive\Desktop\rebuild")
    RAG_BASE = REBUILD_DIR if REBUILD_DIR.exists() else DATA_DIR

# Philosophy 파일 경로
# app/data/philosophy/ 또는 rebuild/philosophy/
if (RAG_BASE / "philosophy").exists():
    PHILOSOPHY_DIR = RAG_BASE / "philosophy"
elif (DATA_DIR / "philosophy").exists():
    PHILOSOPHY_DIR = DATA_DIR / "philosophy"
else:
    PHILOSOPHY_DIR = RAG_BASE

# Portfolio/Macro 파일 경로
# app/data/history/ 또는 rebuild/
if (RAG_BASE / "history").exists():
    HISTORY_DIR = RAG_BASE / "history"
elif (DATA_DIR / "history").exists():
    HISTORY_DIR = DATA_DIR / "history"
else:
    HISTORY_DIR = RAG_BASE

PORTFOLIO_MACRO_FILE = HISTORY_DIR / "guru_portfolio_with_macro.jsonl"
KR_MACRO_FILE = HISTORY_DIR / "kr_macro_quarterly.jsonl"
US_MACRO_FILE = HISTORY_DIR / "us_macro_quarterly.jsonl"  # 향후 추가 예정
US_MACRO_CSV_FILE = HISTORY_DIR / "us_macro_rates.csv"

logger.info(f"[RAG_SERVICE] Using RAG data directory: {RAG_BASE}")
logger.info(f"[RAG_SERVICE] Philosophy directory: {PHILOSOPHY_DIR}")
logger.info(f"[RAG_SERVICE] Portfolio file: {PORTFOLIO_MACRO_FILE} (exists: {PORTFOLIO_MACRO_FILE.exists()})")
logger.info(f"[RAG_SERVICE] KR Macro file: {KR_MACRO_FILE} (exists: {KR_MACRO_FILE.exists()})")
logger.info(f"[RAG_SERVICE] US Macro file: {US_MACRO_FILE} (exists: {US_MACRO_FILE.exists()})")
logger.info(f"[RAG_SERVICE] US Macro CSV file: {US_MACRO_CSV_FILE} (exists: {US_MACRO_CSV_FILE.exists()})")


# ============================================================================
# 초기 로딩 캐시 구조
# ============================================================================

# 전역 캐시: 서버 시작 시 한 번만 로딩
_philosophy_cache: Dict[str, List[Dict[str, Any]]] = {}  # {guru_id: [rows]}
_portfolio_cache: List[Dict[str, Any]] = []  # 전체 포트폴리오 히스토리
_macro_cache: Dict[str, List[Dict[str, Any]]] = {}  # {region: [rows]}
_cache_initialized = False


def _read_jsonl_safe(path: Path) -> List[Dict[str, Any]]:
    """JSONL 파일을 안전하게 읽기 (초기 로딩 전용)"""
    if not path.exists():
        logger.warning(f"JSONL not found: {path}")
        return []
    
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        logger.error(f"JSONL read failed: {path} -> {exc}")
        return []
    
    rows: List[Dict[str, Any]] = []
    for idx, raw in enumerate(text.splitlines(), start=1):
        line = raw.replace("\ufeff", "").strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception as exc:
            logger.warning(f"JSONL parse skip {path.name}:{idx} -> {exc}")
            continue
    
    return rows




def _parse_float(value: Any) -> Optional[float]:
    """쉼표 등이 포함된 문자열을 float로 변환합니다."""
    if value in (None, "", "-", "--"):
        return None
    try:
        text_value = str(value).replace(',', '')
        return float(text_value)
    except Exception:
        return None


def _read_macro_csv(path: Path, region: str) -> List[Dict[str, Any]]:
    """CSV 포맷의 매크로 데이터를 표준 구조로 변환합니다."""
    if not path.exists():
        return []

    rows: List[Dict[str, Any]] = []
    try:
        with path.open(encoding='utf-8', newline='') as handle:
            reader = csv.DictReader(handle)
            for raw in reader:
                period = (raw.get('period') or raw.get('date') or raw.get('quarter') or '').strip()
                if not period:
                    continue
                row: Dict[str, Any] = {'region': region, 'period': period}
                for key in ('base_rate', 'cpi_yoy', 'gdp_growth', 'usdkrw_avg', 'fx_krw_usd', 'unemployment'):
                    parsed = _parse_float(raw.get(key))
                    if parsed is not None:
                        row[key] = parsed
                summary = raw.get('summary')
                if summary:
                    row['summary'] = summary.strip()
                notes = raw.get('notes')
                if notes:
                    row.setdefault('metadata', {})
                    row['metadata']['notes'] = notes.strip()
                rows.append(row)
    except Exception as exc:
        logger.error(f"[RAG_SERVICE] Failed to read macro CSV {path}: {exc}", exc_info=True)
        return []

    return rows

def _normalize_guru_id_in_metadata(metadata: Dict[str, Any]) -> str:
    """메타데이터의 guru_id를 정규화 (cathie → wood)"""
    guru_id = metadata.get("guru_id", "")
    if not guru_id:
        return ""
    
    normalized = normalize_mentor_id(guru_id)
    return normalized


def initialize_rag_cache() -> None:
    """
    서버 시작 시 RAG 데이터를 한 번만 로딩하여 메모리 캐시에 저장.
    이후 요청에서는 파일을 다시 읽지 않음.
    """
    global _philosophy_cache, _portfolio_cache, _macro_cache, _cache_initialized
    
    if _cache_initialized:
        logger.debug("[RAG_SERVICE] Cache already initialized, skipping")
        return
    
    logger.info("[RAG_SERVICE] Initializing RAG cache...")
    
    # 1. Philosophy 파일들 로딩
    file_map = {
        "buffett": "guru_philosophy_buffett.jsonl",
        "lynch": "guru_philosophy_lynch.jsonl",
        "wood": "guru_philosophy_cathie.jsonl",  # cathie → wood
    }
    
    for guru_id, filename in file_map.items():
        path = PHILOSOPHY_DIR / filename
        if path.exists():
            rows = _read_jsonl_safe(path)
            # guru_id 정규화
            normalized_rows = []
            for row in rows:
                metadata = row.get("metadata", {})
                row_guru_id = _normalize_guru_id_in_metadata(metadata)
                if row_guru_id == guru_id:
                    normalized_rows.append(row)
            _philosophy_cache[guru_id] = normalized_rows
            logger.info(f"[RAG_SERVICE] Loaded {len(normalized_rows)} philosophy rows for {guru_id}")
        else:
            logger.warning(f"[RAG_SERVICE] Philosophy file not found: {path}")
            _philosophy_cache[guru_id] = []
    
    # 2. Portfolio 히스토리 로딩
    if PORTFOLIO_MACRO_FILE.exists():
        all_rows = _read_jsonl_safe(PORTFOLIO_MACRO_FILE)
        # portfolio_snapshot 또는 portfolio_history 필터링
        # 파일 구조: section="portfolio_snapshot" 또는 doc_type="portfolio_history"
        _portfolio_cache = [
            row for row in all_rows
            if row.get("doc_type") == "portfolio_history" 
            or row.get("section") == "portfolio_snapshot"
        ]
        logger.info(f"[RAG_SERVICE] Loaded {len(_portfolio_cache)} portfolio history rows")
        if len(_portfolio_cache) == 0 and len(all_rows) > 0:
            # 디버깅: 첫 번째 row의 구조 확인
            logger.warning(
                f"[RAG_SERVICE] No portfolio rows found. "
                f"First row keys: {list(all_rows[0].keys())}, "
                f"doc_type: {all_rows[0].get('doc_type')}, "
                f"section: {all_rows[0].get('section')}"
            )
    else:
        logger.warning(f"[RAG_SERVICE] Portfolio file not found: {PORTFOLIO_MACRO_FILE}")
        _portfolio_cache = []
    
    # 3. Macro 레짐 로딩 (KR)
    if KR_MACRO_FILE.exists():
        kr_rows = _read_jsonl_safe(KR_MACRO_FILE)
        _macro_cache["KR"] = kr_rows
        logger.info(f"[RAG_SERVICE] Loaded {len(kr_rows)} KR macro regime rows")
    else:
        logger.warning(f"[RAG_SERVICE] KR macro file not found: {KR_MACRO_FILE}")
        _macro_cache["KR"] = []
    
    # 4. Macro 데이터 로드 (US) - JSONL + CSV 병합
    us_rows: List[Dict[str, Any]] = []
    if US_MACRO_FILE.exists():
        us_rows = _read_jsonl_safe(US_MACRO_FILE)
        logger.info(f"[RAG_SERVICE] Loaded {len(us_rows)} US macro regime rows")
    else:
        logger.warning(f"[RAG_SERVICE] US macro file not found: {US_MACRO_FILE}")

    csv_rows: List[Dict[str, Any]] = []
    if US_MACRO_CSV_FILE.exists():
        csv_rows = _read_macro_csv(US_MACRO_CSV_FILE, region="US")
        logger.info(f"[RAG_SERVICE] Loaded {len(csv_rows)} US macro rows from CSV")
    elif not us_rows:
        logger.debug("[RAG_SERVICE] US macro CSV file not found; no US macro data available")

    if csv_rows:
        period_map: Dict[str, Dict[str, Any]] = {}
        for row in us_rows:
            period = str(row.get("period") or row.get("updated") or f"json-{len(period_map)}")
            period_map[period] = row
        for csv_row in csv_rows:
            period = str(csv_row.get("period") or f"csv-{len(period_map)}")
            base = period_map.get(period)
            if base:
                for key, value in csv_row.items():
                    if key == "metadata":
                        if value:
                            meta = base.setdefault("metadata", {})
                            for meta_key, meta_val in value.items():
                                if meta_key not in meta or not meta[meta_key]:
                                    meta[meta_key] = meta_val
                    elif value not in (None, "", []):
                        base[key] = value
            else:
                period_map[period] = csv_row
        us_rows = sorted(period_map.values(), key=lambda x: str(x.get("period", "")), reverse=True)

    _macro_cache["US"] = us_rows

    _cache_initialized = True
    logger.info("[RAG_SERVICE] RAG cache initialization complete")


# ============================================================================
# Intent 기반 필터링 함수들
# ============================================================================

def _score_relevance_for_intent(
    row: Dict[str, Any],
    intent: Optional[Intent],
    topic_keywords: Optional[List[str]] = None,
) -> float:
    """Intent와 topic_keywords를 기반으로 row의 관련성 점수를 계산"""
    if intent is None and not topic_keywords:
        return 1.0
    
    # 여러 필드명 지원: page_content, text, content
    row_text = row.get("page_content") or row.get("text") or row.get("content") or ""
    content = (row_text + " " + str(row.get("metadata", {}))).lower()
    score = 0.0
    
    # Intent 기반 키워드 매핑
    intent_keywords = {
        Intent.COMPANY_METRICS: ["per", "pbr", "roe", "eps", "현재가", "주가", "지표"],
        Intent.COMPANY_ANALYSIS: ["valuation", "per", "pbr", "roe", "기업", "종목", "주식", "밸류에이션", "평가", "분석"],
        Intent.COMPARE_COMPANIES: ["compare", "comparison", "비교", "대비"],
        Intent.MACRO_OUTLOOK: ["macro", "economy", "금리", "인플레이션", "경기", "시황", "매크로", "기준금리", "물가", "환율"],
        Intent.PHILOSOPHY: ["philosophy", "principle", "철학", "원칙", "주주서한", "책", "인터뷰"],
        Intent.NEWS_ANALYSIS: ["news", "뉴스", "이슈", "이벤트"],
        Intent.RESEARCH_ANALYSIS: ["research", "report", "리서치", "리포트", "분석"],
    }
    
    if intent:
        keywords = intent_keywords.get(intent, [])
        for kw in keywords:
            if kw in content:
                score += 0.3
    
    # topic_keywords 매칭 (가중치 증가)
    if topic_keywords:
        for kw in topic_keywords:
            kw_lower = kw.lower()
            # 정확한 단어 매칭 (부분 문자열이 아닌)
            if kw_lower in content:
                # 중요한 키워드(inflation, 인플레이션)는 더 높은 가중치
                if kw_lower in ["inflation", "인플레이션"]:
                    score += 2.0  # 매우 높은 가중치 (인플레이션은 핵심 키워드)
                elif kw_lower in ["경제", "economy", "금리", "물가"]:
                    score += 1.0  # 높은 가중치
                else:
                    score += 0.5  # 일반 키워드
    
    return min(score, 5.0)  # 최대 점수 증가 (인플레이션 같은 중요한 키워드가 여러 번 매칭될 수 있음)


def get_guru_philosophy_snippets(
    guru_id: MentorId,
    intent: Optional[Intent] = None,
    query: str = "",
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    멘토 철학 스니펫을 Intent/query 기반으로 필터링하여 반환.
    
    Args:
        guru_id: 멘토 ID
        intent: Intent (선택적)
        query: 사용자 질문 (키워드 추출용)
        top_k: 반환할 스니펫 개수
        
    Returns:
        Dict 리스트 (page_content, metadata 등 포함)
    """
    if not _cache_initialized:
        initialize_rag_cache()
    
    guru_id = normalize_mentor_id(guru_id)
    
    rows = _philosophy_cache.get(guru_id, [])
    if not rows:
        logger.debug(f"[RAG_SERVICE] No philosophy data for {guru_id}")
        return []
    
    # Query에서 키워드 추출 (경제 관련 키워드 확장)
    topic_keywords = []
    if query:
        query_lower = query.lower()
        keywords = [
            # 경제/시장 관련
            "인플레이션", "inflation", "경제", "economy", "경기", "시장", "market",
            "금리", "interest rate", "물가", "cpi", "gdp", "환율", "exchange rate",
            # 투자 관련
            "배당", "dividend", "성장", "growth", "밸류에이션", "valuation", 
            "안전마진", "margin", "비즈니스", "business",
            # 과거/역사 관련
            "과거", "past", "역사", "history", "전망", "outlook", "예측", "prediction"
        ]
        topic_keywords = [kw for kw in keywords if kw in query_lower]
    
    # Intent/topic 기반 점수 계산 및 정렬
    scored_rows = []
    for row in rows:
        row_text = (row.get("page_content") or row.get("text") or row.get("content") or "").lower()
        score = _score_relevance_for_intent(row, intent, topic_keywords)
        
        # 추가: query에 직접 키워드가 포함된 경우 점수 가중치 추가
        if query:
            # query의 주요 단어들이 row_text에 포함되어 있으면 점수 증가
            query_words = query_lower.split()
            for word in query_words:
                if len(word) > 2 and word in row_text:  # 2글자 이상인 단어만
                    score += 0.5  # 직접 매칭 가중치
        
        # 인플레이션 관련 질문인 경우: 실제로 키워드가 있는 문서만 포함
        if query and ("인플레이션" in query_lower or "inflation" in query_lower):
            has_inflation = "inflation" in row_text or "인플레이션" in row_text
            if not has_inflation:
                score = 0  # 인플레이션 키워드가 없으면 점수 0
        
        # 점수가 0보다 큰 문서만 포함
        if score > 0:
            scored_rows.append((score, row))
    
    scored_rows.sort(key=lambda x: x[0], reverse=True)
    
    snippets = []
    for score, row in scored_rows[:top_k]:
        snippets.append(row)
    
    # 디버깅: 인플레이션 관련 질문인 경우 매칭된 스니펫 수 로그
    if query and ("인플레이션" in query_lower or "inflation" in query_lower):
        matched_count = sum(1 for score, _ in scored_rows if score > 0)
        top_scores = [score for score, _ in scored_rows[:10]]
        logger.info(
            f"[RAG_SERVICE] Inflation query matched {matched_count} snippets "
            f"(returning top {len(snippets)}, top scores: {top_scores[:5]})"
        )
    
    logger.info(
        f"[RAG_SERVICE] philosophy snippets used: "
        f"{{guru_id={guru_id}, intent={intent}, count={len(snippets)}}}"
    )
    return snippets


def get_portfolio_history(
    guru_id: MentorId,
    symbol: Optional[str] = None,
    period_range: Optional[tuple[str, str]] = None,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    포트폴리오 히스토리를 필터링하여 반환.
    
    Args:
        guru_id: 멘토 ID
        symbol: 종목 심볼 (선택적)
        period_range: (시작 기간, 종료 기간) 튜플 (선택적)
        top_k: 반환할 레코드 개수
        
    Returns:
        Dict 리스트 (원본 데이터 구조 유지)
    """
    if not _cache_initialized:
        initialize_rag_cache()
    
    guru_id = normalize_mentor_id(guru_id)
    
    filtered = []
    for row in _portfolio_cache:
        row_guru_id = normalize_mentor_id(row.get("guru_id", ""))
        if row_guru_id != guru_id:
            continue
        
        if symbol:
            # symbols 필드 (리스트) 또는 holdings 필드 (리스트)에서 매칭
            symbols_list = row.get("symbols", [])
            holdings = row.get("holdings", [])
            
            # symbols 리스트에서 매칭 시도
            symbol_matched = False
            if isinstance(symbols_list, list):
                symbol_matched = any(
                    str(s).upper() == symbol.upper() or 
                    str(s).upper().endswith(f".{symbol.upper()}") or
                    symbol.upper() in str(s).upper()
                    for s in symbols_list
                )
            
            # holdings 리스트에서 매칭 시도 (symbols에서 못 찾은 경우)
            if not symbol_matched and isinstance(holdings, list):
                symbol_matched = any(
                    str(h).upper() == symbol.upper() or 
                    str(h).upper().endswith(f".{symbol.upper()}") or
                    symbol.upper() in str(h).upper()
                    for h in holdings
                )
            
            if not symbol_matched:
                continue
        
        if period_range:
            from_period, to_period = period_range
            as_of = row.get("as_of", "")
            if from_period and as_of < from_period:
                continue
            if to_period and as_of > to_period:
                continue
        
        filtered.append(row)
    
    filtered.sort(key=lambda x: x.get("as_of", ""), reverse=True)
    
    result = filtered[:top_k]
    
    logger.info(
        f"[RAG_SERVICE] portfolio rows used: "
        f"{{guru_id={guru_id}, symbol={symbol}, count={len(result)}}}"
    )
    return result


def get_macro_regime(
    region: str = "KR",
    last_n_quarters: int = 4,
) -> List[Dict[str, Any]]:
    """
    매크로 레짐 스냅샷을 최근 N개 분기만 반환.
    
    Args:
        region: "KR" 또는 "US"
        last_n_quarters: 최근 몇 개 분기를 반환할지
        
    Returns:
        Dict 리스트 (period, base_rate, cpi_yoy, gdp_growth, fx_krw_usd, unemployment 등 포함)
    """
    if not _cache_initialized:
        initialize_rag_cache()
    
    rows = _macro_cache.get(region, [])
    if not rows:
        logger.debug(f"[RAG_SERVICE] No macro data for region {region}")
        return []
    
    filtered = [r for r in rows if r.get("region") == region]
    filtered.sort(key=lambda x: x.get("period", ""), reverse=True)
    
    result = filtered[:last_n_quarters]
    
    logger.info(
        f"[RAG_SERVICE] macro rows used: "
        f"{{region={region}, count={len(result)}}}"
    )
    return result


# 하위 호환성을 위한 별칭
def get_macro_regime_snippets(region: str, last_n: int = 4) -> List[Dict[str, Any]]:
    """하위 호환성: get_macro_regime의 별칭"""
    return get_macro_regime(region=region, last_n_quarters=last_n)

