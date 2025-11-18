# app/services/orchestration_graph.py
"""
LangGraph 기반 오케스트레이션

워크플로우:
START → Router → [Intent별 분기] → LangChain RAG Node → Validator Loop → REST API → Mentor Agent → END

주요 구성 요소:
- Router: Intent 라우팅
- LangChain RAG Node: BM25 retriever + stuff-documents chain + validator chain
- Validator Loop: 검증 실패 시 재시도 또는 개선
- REST API Node: 외부 API 호출 (Kiwoom 등)
- Mentor Agent Node: 최종 응답 생성
"""

from __future__ import annotations

import logging
import re
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from app.mentors.types import Intent, RoutedQuery, StockMetrics
from app.mentors.router import route_query
from app.mentors.registry import get_mentor_agent
from app.services.langchain_rag import run_rag_pipeline
from app.services.rag_service import (
    get_guru_philosophy_snippets,
    get_macro_regime,
    get_portfolio_history,
    initialize_rag_cache,
)
from app.services.kiwoom_client import KiwoomClient
from app.services.chatbot_service import _normalise_live_snapshot
from app.services.pykrx_metrics_service import compute_peg_ratio
from app.services.llm_service import invoke_llm
from app.utils.mentor_utils import normalize_mentor_id

logger = logging.getLogger(__name__)

REGION_LABELS = {
    "KR": "한국",
    "US": "미국",
}


MACRO_RECORD_LIMIT = 4

CONTEXT_WORDS = ("왜", "어떻게", "어때", "요즘", "분석", "전망", "매수", "매도", "살까", "팔까", "분해", "설명", "해석")
QUESTION_HINTS = ("얼마", "알려", "가르쳐", "말해", "?", "몇", "구해", "궁금", "주세요")
PRICE_KEYWORDS = ("현재가", "주가")

METRIC_CONFIG = {
    "PER": {
        "keywords": ["PER", "피이알"],
        "attr": "pe",
        "display": "PER",
        "unit": "배",
        "decimals": 2,
    },
    "PBR": {
        "keywords": ["PBR", "피비알"],
        "attr": "pb",
        "display": "PBR",
        "unit": "배",
        "decimals": 2,
    },
    "EPS": {
        "keywords": ["EPS", "주당순이익", "주당 순이익"],
        "attr": "eps",
        "display": "EPS",
        "unit": "원",
        "decimals": 0,
    },
    "BPS": {
        "keywords": ["BPS", "주당순자산", "주당 순자산"],
        "attr": "bps",
        "display": "BPS",
        "unit": "원",
        "decimals": 0,
    },
    "ROE": {
        "keywords": ["ROE", "자기자본이익률"],
        "attr": "roe",
        "display": "ROE",
        "unit": "%",
        "decimals": 2,
    },
    "DIV_YIELD": {
        "keywords": ["배당수익률", "배당 수익률", "배당률"],
        "attr": "div_yield",
        "display": "배당수익률",
        "unit": "%",
        "decimals": 2,
    },
    "PEG": {
        "keywords": ["PEG", "피이지"],
        "attr": "peg",
        "display": "PEG",
        "unit": "",
        "decimals": 2,
    },
}


def _has_context_word(text: str) -> bool:
    return any(word in text for word in CONTEXT_WORDS)


def _has_question_hint(text: str) -> bool:
    return any(word in text for word in QUESTION_HINTS)


def _is_price_only_question(message: str | None) -> bool:
    if not message:
        return False
    text = message.strip()
    if not text:
        return False
    if not any(word in text for word in PRICE_KEYWORDS):
        return False
    if _has_context_word(text):
        return False
    return _has_question_hint(text)


def _detect_metric_request(message: str | None) -> Optional[str]:
    if not message:
        return None
    text = message.strip()
    if not text or _has_context_word(text) or not _has_question_hint(text):
        return None
    upper_text = text.upper()
    compact_text = re.sub(r"\s+", "", upper_text)
    for key, cfg in METRIC_CONFIG.items():
        for keyword in cfg.get("keywords", []):
            kw_upper = keyword.upper()
            if kw_upper in upper_text or kw_upper.replace(" ", "") in compact_text:
                return key
    return None


def _format_price_response(metric: StockMetrics, fallback_symbol: List[str] | None) -> str:
    display_name = metric.name or metric.symbol or (fallback_symbol[0] if fallback_symbol else "")
    price = metric.price
    if price is None:
        target = f"{display_name} " if display_name else ""
        return f"{target}현재가 정보를 불러오지 못했습니다."
    if isinstance(price, (int, float)):
        price_text = f"{price:,.0f}원"
    else:
        price_text = str(price)
    prefix = f"{display_name} " if display_name else ""
    return f"{prefix}현재가는 {price_text}입니다."


def _format_peg_response(
    metric: StockMetrics,
    fallback_symbol: List[str] | None,
    peg_value: Optional[float] = None,
    eps_growth: Optional[float] = None,
) -> str:
    display_name = metric.name or metric.symbol or (fallback_symbol[0] if fallback_symbol else "")
    subject = display_name or "해당 종목"
    peg_value = peg_value if peg_value is not None else metric.peg
    eps_growth = eps_growth if eps_growth is not None else metric.eps_growth_percent
    if peg_value is None:
        if eps_growth is None:
            return f"{subject} PEG를 계산하려면 최신 EPS 성장률이 필요한데 pykrx 데이터에서 값을 찾지 못했습니다."
        return f"{subject} PEG는 최근 EPS 성장률이 0 이하라 계산할 수 없습니다."
    if isinstance(peg_value, (int, float)):
        peg_text = f"{peg_value:.2f}"
    else:
        peg_text = str(peg_value)
    parts = [f"{subject} PEG는 {peg_text}입니다."]
    if isinstance(eps_growth, (int, float)):
        parts.append(f"(EPS 성장률 {eps_growth:.1f}% 기반)")
    return " ".join(parts)


def _format_metric_value(value: object, decimals: Optional[int]) -> str:
    if isinstance(value, (int, float)):
        if decimals is None:
            return str(value)
        if decimals == 0:
            return f"{value:,.0f}"
        return f"{value:,.{decimals}f}"
    return str(value)


async def _format_metric_response(
    metric: StockMetrics,
    metric_key: str,
    fallback_symbol: List[str] | None,
) -> str:
    name = metric.name or metric.symbol or (fallback_symbol[0] if fallback_symbol else "")
    subject_prefix = f"{name} " if name else ""
    if metric_key == "PEG":
        peg_override = metric.peg
        growth_override = metric.eps_growth_percent
        if peg_override is None and symbol and symbol.isdigit():
            try:
                peg_override, growth_override = await compute_peg_ratio(symbol, metric.pe)
            except Exception as exc:
                logger.error(f"Failed to recompute PEG for {symbol}: {exc}", exc_info=True)
        return _format_peg_response(metric, fallback_symbol, peg_override, growth_override)

    cfg = METRIC_CONFIG.get(metric_key)
    if not cfg:
        return f"{subject_prefix}{metric_key} 정보를 지원하지 않습니다."
    attr = cfg.get("attr")
    value = getattr(metric, attr, None)
    if value is None:
        return f"{subject_prefix}{cfg.get('display', metric_key)} 정보를 불러오지 못했습니다."
    value_text = _format_metric_value(value, cfg.get("decimals", 2))
    unit = cfg.get("unit", "")
    if unit:
        value_text = f"{value_text}{unit}"
    display_name = cfg.get("display", metric_key)
    return f"{subject_prefix}{display_name}은 {value_text}입니다."

def _build_macro_coverage_record(region: str, rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Builds a coverage summary entry for macro data."""
    if not rows:
        return None
    periods: List[str] = []
    for record in rows:
        if not isinstance(record, dict):
            continue
        period = record.get("period")
        if not period:
            continue
        periods.append(str(period).strip())
    if not periods:
        return None
    latest = periods[0]
    earliest = periods[-1]
    total = len(periods)
    region_label = REGION_LABELS.get(region, region or "default")
    summary = f"{region_label} 데이터 커버리지: {earliest} ~ {latest} (총 {total}개 분기)"
    return {
        "region": region,
        "period": "데이터 커버리지",
        "summary": summary,
        "record_type": "coverage_summary",
        "metadata": {
            "coverage": {
                "start": earliest,
                "end": latest,
                "total_rows": total,
            }
        },
    }

def _format_macro_record(record: Dict[str, Any]) -> str:
    """매크로 RAG 레코드를 사람이 읽을 수 있는 텍스트로 변환."""
    region = record.get("region", "")
    region_label = REGION_LABELS.get(region, region or "기타 지역")
    period = record.get("period", "N/A")
    summary = record.get("summary") or record.get("text") or record.get("page_content") or ""

    # indicators는 record 또는 metadata에 존재할 수 있음
    indicators: Dict[str, Any] = {}
    raw_indicators = record.get("indicators")
    if isinstance(raw_indicators, dict):
        indicators.update(raw_indicators)
    metadata = record.get("metadata", {}) or {}
    meta_indicators = metadata.get("indicators")
    if isinstance(meta_indicators, dict):
        for key, value in meta_indicators.items():
            indicators.setdefault(key, value)

    # 상위 필드 일부를 indicators에 병합
    for key in (
        "base_rate",
        "cpi_yoy",
        "gdp_growth",
        "usdkrw_avg",
        "fx_krw_usd",
        "unemployment",
        "unemployment_rate_percent",
    ):
        if key in record:
            indicators.setdefault(key, record[key])

    indicator_labels = {
        "base_rate": "기준금리(%)",
        "cpi_yoy": "물가상승률(%)",
        "gdp_growth": "GDP 성장률(%)",
        "usdkrw_avg": "원/달러 평균환율",
        "fx_krw_usd": "원/달러 환율",
        "unemployment": "실업률(%)",
        "unemployment_rate_percent": "실업률(%)",
        "m2_krw_billion": "M2(십억 KRW)",
        "export_price_index_2020_100": "수출물가(2020=100)",
        "import_price_index_2020_100": "수입물가(2020=100)",
        "gdp_nominal_krw_billion": "명목 GDP(십억 KRW)",
    }

    lines = [f"[RAG: Macro-{region_label}] {period} 경제지표"]
    if indicators:
        lines.append("지표:")
        for key, value in indicators.items():
            label = indicator_labels.get(key, key)
            lines.append(f"- {label}: {value}")

    if metadata:
        source = metadata.get("source") or metadata.get("dataset")
        if source:
            lines.append(f"- source: {source}")
        if metadata.get("notes"):
            lines.append(f"- notes: {metadata['notes']}")

    if summary:
        lines.append("요약: " + summary.strip())

    return "\n".join(lines)


class OrchestrationState(TypedDict):
    """오케스트레이션 상태"""
    messages: Annotated[List, add_messages]
    user_message: str
    guru_id: str
    session_id: Optional[str]
    routed_query: Optional[RoutedQuery]
    # RAG 관련 필드 (LangChain RAG 파이프라인 결과)
    rag_docs: List[dict]  # 검색된 문서들
    draft_answer: Optional[str]  # RAG chain의 초안 답변
    validated_answer: Optional[str]  # Validator를 통과한 최종 답변
    rag_is_valid: bool  # RAG 검증 결과
    rag_confidence: float  # RAG 신뢰도
    rag_issues: List[str]  # RAG 검증 이슈
    # 레거시 RAG 필드 (rag_service에서 직접 로드한 데이터)
    philosophy_snippets: List[dict]
    portfolio_history: List[dict]
    macro_data: List[dict]
    stock_metrics: List[StockMetrics]
    response: Optional[str]


def router_node(state: OrchestrationState) -> Dict:
    """Intent 라우팅 노드"""
    user_message = state["user_message"]
    guru_id = state["guru_id"]
    
    logger.info(f"[ORCHESTRATION] Routing: message='{user_message[:50]}...', guru={guru_id}")
    
    routed_query = route_query(user_message, guru_id)
    
    logger.info(
        f"[ORCHESTRATION] Routed: intent={routed_query.intent.value}, "
        f"mentor={routed_query.mentor_id}, symbols={routed_query.symbols}, "
        f"region={routed_query.region}"
    )
    
    return {
        "routed_query": routed_query,
    }


async def langchain_rag_node(state: OrchestrationState) -> Dict:
    """
    LangChain RAG 파이프라인 노드
    
    BM25 retriever → stuff-documents chain → validator chain 실행
    """
    routed_query = state.get("routed_query")
    if not routed_query:
        return {}
    
    intent = routed_query.intent
    mentor_id = routed_query.mentor_id
    user_message = state["user_message"]
    
    # LangChain RAG 파이프라인 실행
    try:
        rag_result = await run_rag_pipeline(
            query=user_message,
            guru_id=mentor_id,
            intent=intent,
            top_k=5,
        )
        
        # Document를 dict로 변환 (직렬화 가능하도록)
        docs_dict = []
        for doc in rag_result.get("docs", []):
            docs_dict.append({
                "page_content": doc.page_content,
                "metadata": doc.metadata,
            })
        
        logger.info(
            f"[ORCHESTRATION] LangChain RAG completed: "
            f"docs={len(docs_dict)}, valid={rag_result.get('is_valid')}, "
            f"confidence={rag_result.get('confidence', 0.0):.2f}"
        )
        
        return {
            "rag_docs": docs_dict,
            "draft_answer": rag_result.get("draft_answer", ""),
            "validated_answer": rag_result.get("validated_answer", ""),
            "rag_is_valid": rag_result.get("is_valid", False),
            "rag_confidence": rag_result.get("confidence", 0.0),
            "rag_issues": rag_result.get("issues", []),
        }
    except Exception as exc:
        logger.error(f"LangChain RAG pipeline failed: {exc}", exc_info=True)
        return {
            "rag_docs": [],
            "draft_answer": "",
            "validated_answer": "죄송합니다. RAG 처리 중 오류가 발생했습니다.",
            "rag_is_valid": False,
            "rag_confidence": 0.0,
            "rag_issues": [f"RAG 처리 오류: {exc}"],
        }


async def rag_loader_node(state: OrchestrationState) -> Dict:
    """
    레거시 RAG 데이터 로딩 노드 (포트폴리오/매크로 데이터용)
    
    LangChain RAG는 philosophy 데이터를 처리하고,
    이 노드는 포트폴리오 히스토리와 매크로 데이터를 로드합니다.
    """
    routed_query = state.get("routed_query")
    if not routed_query:
        return {}
    
    intent = routed_query.intent
    mentor_id = routed_query.mentor_id
    symbols = routed_query.symbols
    region = routed_query.region or "KR"
    user_message = state["user_message"]
    
    philosophy_snippets: List[dict] = []
    portfolio_history: List[dict] = []
    macro_data: List[dict] = []
    
    # RAG 캐시 초기화 확인
    initialize_rag_cache()
    
    # Intent별 추가 RAG 로딩 (포트폴리오/매크로)
    if intent == Intent.HISTORICAL_DATA:
        # Historical Data: 포트폴리오 히스토리 로드
        try:
            # 특정 종목이 있으면 해당 종목의 포트폴리오 히스토리만, 없으면 전체 포트폴리오
            if symbols:
                portfolio_history = get_portfolio_history(
                    mentor_id,
                    symbol=symbols[0],
                    top_k=5,  # 최신 5개
                )
            else:
                # 전체 포트폴리오 히스토리 (최신순)
                portfolio_history = get_portfolio_history(
                    mentor_id,
                    symbol=None,
                    top_k=10,  # 최신 10개
                )
            logger.info(f"[ORCHESTRATION] Loaded {len(portfolio_history)} portfolio history records")
        except Exception as exc:
            logger.warning(f"Portfolio history not available: {exc}", exc_info=True)
    
    elif intent in (Intent.COMPANY_ANALYSIS, Intent.COMPARE_COMPANIES, Intent.NEWS_ANALYSIS, Intent.RESEARCH_ANALYSIS):
        # 종목 분석 관련: 특정 종목의 포트폴리오 히스토리만 로드
        if symbols:
            try:
                portfolio_history = get_portfolio_history(
                    mentor_id,
                    symbol=symbols[0],
                    top_k=3,
                )
                logger.info(f"[ORCHESTRATION] Loaded {len(portfolio_history)} portfolio history records for symbol {symbols[0]}")
            except Exception as exc:
                logger.debug(f"Portfolio history not available: {exc}")
    
    elif intent == Intent.MACRO_OUTLOOK:
        # 매크로 분석: 요청된 지역의 지표를 로드
        preferred_regions = routed_query.macro_regions or ([region] if region else None)
        if not preferred_regions:
            preferred_regions = ["KR"]
        try:
            macro_records: List[dict] = []
            for macro_region in preferred_regions:
                rows_full = get_macro_regime(region=macro_region, last_n_quarters=None)
                if not rows_full:
                    logger.info(
                        "[ORCHESTRATION] No macro rows available for region=%s",
                        macro_region,
                    )
                    continue
                coverage_record = _build_macro_coverage_record(macro_region, rows_full)
                if coverage_record:
                    macro_records.append(coverage_record)
                if MACRO_RECORD_LIMIT and MACRO_RECORD_LIMIT > 0:
                    rows = rows_full[:MACRO_RECORD_LIMIT]
                else:
                    rows = rows_full
                macro_records.extend(rows)
                logger.info(
                    "[ORCHESTRATION] Loaded %s macro records for region=%s (cached_total=%s)",
                    len(rows),
                    macro_region,
                    len(rows_full),
                )
            macro_data = macro_records
        except Exception as exc:
            logger.error(f"Failed to load macro regime: {exc}", exc_info=True)
    
    logger.info(
        f"[ORCHESTRATION] Legacy RAG loaded: "
        f"portfolio={len(portfolio_history)}, macro={len(macro_data)}"
    )
    
    return {
        "portfolio_history": portfolio_history,
        "macro_data": macro_data,
    }


async def rest_api_node(state: OrchestrationState) -> Dict:
    """REST API 호출 노드 (Kiwoom 등)"""
    routed_query = state.get("routed_query")
    if not routed_query:
        return {}
    
    intent = routed_query.intent
    symbols = routed_query.symbols
    
    logger.info(f"[ORCHESTRATION] REST API node: intent={intent.value}, symbols={symbols}")
    
    stock_metrics: List[StockMetrics] = []
    
    # Intent별 REST API 호출
    if intent in (Intent.COMPANY_METRICS, Intent.COMPANY_ANALYSIS, Intent.COMPARE_COMPANIES):
        if symbols:
            logger.info(f"[ORCHESTRATION] Attempting to load stock metrics for symbols: {symbols}")
            try:
                client = KiwoomClient()
                for symbol in symbols:
                    try:
                        logger.info(f"[ORCHESTRATION] Calling Kiwoom API for symbol: {symbol}")
                        raw = await client.ka10001(symbol)
                        logger.debug(f"[ORCHESTRATION] Kiwoom API raw response for {symbol}: {raw}")
                        snapshot = _normalise_live_snapshot(raw, symbol)
                        if snapshot:
                            logger.info(f"[ORCHESTRATION] Successfully normalized snapshot for {symbol}")
                            metrics_data = snapshot.get("metadata", {}).get("metrics", {}) or {}
                            peg_ratio = None
                            eps_growth = None
                            if symbol.isdigit() and len(symbol) == 6:
                                try:
                                    peg_ratio, eps_growth = await compute_peg_ratio(symbol, metrics_data.get("PER"))
                                except Exception as exc:
                                    logger.error(f"Failed to compute PEG for {symbol}: {exc}", exc_info=True)
                            metrics = StockMetrics(
                                symbol=symbol,
                                name=snapshot.get("metadata", {}).get("name") or raw.get("stk_nm"),
                                price=metrics_data.get("CUR"),
                                market_cap=metrics_data.get("MKT_CAP"),
                                pe=metrics_data.get("PER"),
                                pb=metrics_data.get("PBR"),
                                eps=metrics_data.get("EPS"),
                                bps=metrics_data.get("BPS"),
                                roe=metrics_data.get("ROE"),
                                div_yield=metrics_data.get("DIV_YIELD"),
                                volume=metrics_data.get("VOL"),
                                trade_value=metrics_data.get("TRADE_VALUE"),
                                high_52w=metrics_data.get("52W_H"),
                                low_52w=metrics_data.get("52W_L"),
                                peg=peg_ratio,
                                eps_growth_percent=eps_growth,
                            )
                            stock_metrics.append(metrics)
                            logger.info(f"[ORCHESTRATION] Loaded metrics for {symbol}: price={metrics.price}, PER={metrics.pe}, PBR={metrics.pb}")
                        else:
                            logger.warning(f"[ORCHESTRATION] Failed to normalize snapshot for {symbol}. Raw response: {raw}")
                    except Exception as exc:
                        logger.error(f"Failed to load metrics for {symbol}: {exc}", exc_info=True)
                await client.close()
            except Exception as exc:
                logger.error(f"Failed to load stock metrics: {exc}", exc_info=True)
        else:
            logger.warning(f"[ORCHESTRATION] No symbols found for intent {intent.value}. Cannot load stock metrics.")
    
    logger.info(f"[ORCHESTRATION] REST API loaded: stock_metrics={len(stock_metrics)}")
    if stock_metrics:
        for m in stock_metrics:
            logger.info(f"[ORCHESTRATION] Final stock_metrics: symbol={m.symbol}, price={m.price}")
    
    return {
        "stock_metrics": stock_metrics,
    }


async def mentor_agent_node(state: OrchestrationState) -> Dict:
    """
    멘토 에이전트 호출 노드
    
    LangChain RAG의 validated_answer를 우선 사용하고,
    추가로 포트폴리오/매크로 데이터를 전달합니다.
    """
    routed_query = state.get("routed_query")
    if not routed_query:
        return {}
    
    mentor_id = routed_query.mentor_id
    intent = routed_query.intent
    symbols = routed_query.symbols
    user_message = state["user_message"]
    
    # LangChain RAG 결과 (validated answer 우선 사용)
    validated_answer = state.get("validated_answer")
    rag_issues = state.get("rag_issues", [])
    
    # 레거시 RAG 데이터
    portfolio_history = state.get("portfolio_history", [])
    macro_data = state.get("macro_data", [])
    macro_texts: List[str] = []
    for record in macro_data:
        try:
            formatted = _format_macro_record(record)
            if formatted:
                macro_texts.append(formatted)
        except Exception as exc:
            logger.debug("Failed to format macro record: %s", exc)
    stock_metrics = state.get("stock_metrics", [])
    
    # 포트폴리오 텍스트 변환 (모든 메타데이터 포함)
    portfolio_texts = []
    for p in portfolio_history:
        # 여러 필드명 지원: page_content, text, content, summary
        text = p.get("page_content") or p.get("text") or p.get("content") or p.get("summary") or ""
        
        # portfolio_snapshot 구조인 경우 metadata.portfolio 정보를 상세하게 변환
        if p.get("section") == "portfolio_snapshot" or p.get("doc_type") == "portfolio_history":
            portfolio_info = p.get("metadata", {}).get("portfolio", {})
            as_of = p.get("as_of", "N/A")
            
            if portfolio_info:
                # 포트폴리오 상세 정보 구성
                total_value = portfolio_info.get("total_equity_value_usd", 0)
                num_positions = portfolio_info.get("num_positions", 0)
                holdings = portfolio_info.get("top_holdings", [])
                
                # 상위 보유 종목 상세 정보
                holdings_details = []
                for h in holdings[:20]:  # 상위 20개 종목
                    name = h.get("name", "")
                    weight = h.get("weight", 0)
                    market_value = h.get("market_value_usd", 0)
                    if name:
                        weight_pct = weight * 100 if weight else 0
                        holdings_details.append(
                            f"{name} (비중: {weight_pct:.2f}%, 시가총액: ${market_value:,.0f})"
                        )
                
                # 포트폴리오 텍스트 구성
                portfolio_parts = [
                    f"포트폴리오 스냅샷 (기준일: {as_of})",
                    f"총 자산 가치: ${total_value:,.0f}",
                    f"보유 종목 수: {num_positions}개",
                    "상위 보유 종목:"
                ]
                portfolio_parts.extend(holdings_details)
                text = "\n".join(portfolio_parts)
            elif text:
                # 기존 text가 있으면 그대로 사용하되, as_of 정보 추가
                if as_of != "N/A":
                    text = f"[기준일: {as_of}]\n{text}"
        
        if text:
            portfolio_texts.append(text)
    
    logger.info(
        f"[ORCHESTRATION] Calling mentor agent: mentor={mentor_id}, intent={intent.value}, "
        f"validated_answer={bool(validated_answer)}, stock_metrics={len(stock_metrics)}, "
        f"portfolio={len(portfolio_texts)}, macro={len(macro_texts)}"
    )
    
    # Handle simple numerical queries without invoking mentor persona
    if stock_metrics:
        metric_key = _detect_metric_request(user_message)
        if metric_key:
            response_text = await _format_metric_response(stock_metrics[0], metric_key, symbols)
            return {
                "response": response_text,
                "messages": [AIMessage(content=response_text)],
            }
        if _is_price_only_question(user_message):
            response_text = _format_price_response(stock_metrics[0], symbols)
            return {
                "response": response_text,
                "messages": [AIMessage(content=response_text)],
            }

    try:
        agent = get_mentor_agent(mentor_id)
        
        # Validated answer가 있으면 이를 context로 전달
        # Mentor agent는 이를 참고하여 최종 응답 생성
        philosophy_texts = []
        if validated_answer:
            # Validated answer를 philosophy snippet처럼 사용
            philosophy_texts.append(f"[RAG 검증된 요약]\n{validated_answer}")
            if rag_issues:
                philosophy_texts.append(f"[검증 이슈]\n" + "\n".join(rag_issues))
        
        response = await agent.generate_response(
            query=user_message,
            intent=intent.value,
            symbols=symbols,
            stock_metrics=stock_metrics if stock_metrics else None,
            macro_data=macro_texts if macro_texts else None,
            philosophy_snippets=philosophy_texts if philosophy_texts else None,
            portfolio_history=portfolio_texts if portfolio_texts else None,
        )
        
        logger.info(f"[ORCHESTRATION] Response generated (length={len(response)})")
        
        return {
            "response": response,
            "messages": [AIMessage(content=response)],
        }
    except Exception as exc:
        logger.error(f"Mentor agent failed: {exc}", exc_info=True)
        error_response = f"죄송합니다. 응답 생성 중 오류가 발생했습니다: {exc}"
        return {
            "response": error_response,
            "messages": [AIMessage(content=error_response)],
        }


def route_by_intent(state: OrchestrationState) -> str:
    """Intent에 따라 다음 노드 결정"""
    routed_query = state.get("routed_query")
    if not routed_query:
        return "mentor_agent"
    
    intent = routed_query.intent
    
    # Historical Data Intent: 포트폴리오/과거 발언 데이터 조회
    if intent == Intent.HISTORICAL_DATA:
        return "rag_loader"
    
    # LangChain RAG가 필요한 Intent (philosophy 관련 질문)
    if intent in (Intent.PHILOSOPHY, Intent.COMPANY_ANALYSIS, Intent.COMPARE_COMPANIES, 
                  Intent.NEWS_ANALYSIS, Intent.RESEARCH_ANALYSIS):
        return "langchain_rag"
    
    # 레거시 RAG 로더가 필요한 Intent (매크로 등)
    if intent == Intent.MACRO_OUTLOOK:
        return "rag_loader"
    
    # REST API가 필요한 Intent
    if intent in (Intent.COMPANY_METRICS, Intent.COMPANY_ANALYSIS, Intent.COMPARE_COMPANIES):
        return "rest_api"
    
    # 그 외는 바로 멘토 에이전트
    return "mentor_agent"


def should_refine_rag(state: OrchestrationState) -> str:
    """
    RAG 검증 결과에 따라 다음 노드 결정
    
    Returns:
        "refine": 검증 실패 시 재시도
        "rag_loader": 검증 성공 시 추가 RAG 로딩 또는 REST API
        "mentor_agent": 바로 멘토 에이전트로
    """
    rag_is_valid = state.get("rag_is_valid", True)
    rag_confidence = state.get("rag_confidence", 1.0)
    
    refinement_count = state.get("_rag_refinement_count", 0)
    needs_refine = (not rag_is_valid) or (rag_confidence < 0.6)
    if needs_refine and refinement_count < 1:
        logger.info(
            "[ORCHESTRATION] RAG validation insufficient (valid=%s, confidence=%.2f), "
            "attempting refinement (count=%s)",
            rag_is_valid,
            rag_confidence,
            refinement_count,
        )
        return "refine"
    
    # 검증 성공 또는 재시도 횟수 초과 시 다음 단계로
    routed_query = state.get("routed_query")
    if not routed_query:
        return "mentor_agent"
    
    intent = routed_query.intent
    symbols = routed_query.symbols
    
    # Historical Data Intent는 이미 rag_loader로 라우팅되었으므로 여기서는 처리 불필요
    # (이 함수는 langchain_rag 이후에 호출되므로)
    
    # 추가 RAG 데이터가 필요한 경우 (종목 분석)
    if intent == Intent.COMPANY_ANALYSIS and symbols:
        return "rag_loader"
    
    if intent in (Intent.COMPARE_COMPANIES, Intent.NEWS_ANALYSIS, Intent.RESEARCH_ANALYSIS) and symbols:
        return "rag_loader"
    
    # REST API가 필요한 경우
    if intent in (Intent.COMPANY_METRICS, Intent.COMPANY_ANALYSIS, Intent.COMPARE_COMPANIES) and symbols:
        return "rest_api"
    
    return "mentor_agent"


async def refine_rag_node(state: OrchestrationState) -> Dict:
    """
    RAG 검증 실패 시 재시도 노드
    
    검색 쿼리를 개선하거나 더 많은 문서를 검색하여 재시도합니다.
    """
    routed_query = state.get("routed_query")
    if not routed_query:
        return {}
    
    mentor_id = routed_query.mentor_id
    intent = routed_query.intent
    user_message = state["user_message"]
    rag_issues = state.get("rag_issues", [])
    
    # 재시도 횟수 증가
    refinement_count = state.get("_rag_refinement_count", 0) + 1
    
    # 더 많은 문서를 검색하거나 쿼리를 개선하여 재시도
    try:
        rag_result = await run_rag_pipeline(
            query=user_message,
            guru_id=mentor_id,
            intent=intent,
            top_k=10,  # 더 많은 문서 검색
        )
        
        docs_dict = []
        for doc in rag_result.get("docs", []):
            docs_dict.append({
                "page_content": doc.page_content,
                "metadata": doc.metadata,
            })
        
        logger.info(
            f"[ORCHESTRATION] RAG refinement completed: "
            f"docs={len(docs_dict)}, valid={rag_result.get('is_valid')}, "
            f"confidence={rag_result.get('confidence', 0.0):.2f}"
        )
        
        return {
            "rag_docs": docs_dict,
            "draft_answer": rag_result.get("draft_answer", ""),
            "validated_answer": rag_result.get("validated_answer", ""),
            "rag_is_valid": rag_result.get("is_valid", False),
            "rag_confidence": rag_result.get("confidence", 0.0),
            "rag_issues": rag_result.get("issues", []),
            "_rag_refinement_count": refinement_count,
        }
    except Exception as exc:
        logger.error(f"RAG refinement failed: {exc}", exc_info=True)
        return {
            "_rag_refinement_count": refinement_count,
        }


# LangGraph 워크플로우 구성
workflow = StateGraph(OrchestrationState)

# 노드 추가
workflow.add_node("router", router_node)
workflow.add_node("langchain_rag", langchain_rag_node)
workflow.add_node("refine_rag", refine_rag_node)
workflow.add_node("rag_loader", rag_loader_node)
workflow.add_node("rest_api", rest_api_node)
workflow.add_node("mentor_agent", mentor_agent_node)

# 엣지 추가
workflow.add_edge(START, "router")
workflow.add_conditional_edges(
    "router",
    route_by_intent,
    {
        "langchain_rag": "langchain_rag",
        "rag_loader": "rag_loader",
        "rest_api": "rest_api",
        "mentor_agent": "mentor_agent",
    }
)

# LangChain RAG 후 검증 루프
workflow.add_conditional_edges(
    "langchain_rag",
    should_refine_rag,
    {
        "refine": "refine_rag",
        "rag_loader": "rag_loader",
        "rest_api": "rest_api",
        "mentor_agent": "mentor_agent",
    }
)

# Refine 후 다시 검증 (재시도는 한 번만 하므로 "refine" 경로 제거)
def route_after_refine(state: OrchestrationState) -> str:
    """Refine 후 다음 노드 결정 (재시도 없음)"""
    routed_query = state.get("routed_query")
    if not routed_query:
        return "mentor_agent"
    
    intent = routed_query.intent
    symbols = routed_query.symbols
    
    # 추가 RAG 데이터가 필요한 경우
    if intent in (Intent.COMPANY_ANALYSIS, Intent.COMPARE_COMPANIES) and symbols:
        return "rag_loader"
    
    # REST API가 필요한 경우
    if intent in (Intent.COMPANY_ANALYSIS, Intent.COMPARE_COMPANIES) and symbols:
        return "rest_api"
    
    return "mentor_agent"

workflow.add_conditional_edges(
    "refine_rag",
    route_after_refine,
    {
        "rag_loader": "rag_loader",
        "rest_api": "rest_api",
        "mentor_agent": "mentor_agent",
    }
)

# 레거시 RAG 로더 후 라우팅
def route_after_legacy_rag(state: OrchestrationState) -> str:
    """레거시 RAG 로딩 후 다음 노드 결정"""
    routed_query = state.get("routed_query")
    if not routed_query:
        return "mentor_agent"
    
    intent = routed_query.intent
    symbols = routed_query.symbols
    
    # REST API가 필요한 Intent
    if intent in (Intent.COMPANY_ANALYSIS, Intent.COMPARE_COMPANIES) and symbols:
        return "rest_api"
    
    return "mentor_agent"

workflow.add_conditional_edges(
    "rag_loader",
    route_after_legacy_rag,
    {
        "rest_api": "rest_api",
        "mentor_agent": "mentor_agent",
    }
)

workflow.add_edge("rest_api", "mentor_agent")
workflow.add_edge("mentor_agent", END)

# 컴파일
orchestration_graph = workflow.compile()

