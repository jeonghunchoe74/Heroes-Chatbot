"""Chatbot brain with intentionally simple, well documented building blocks.

The original file grew from many small experiments which made it hard to follow
how a single answer was produced.  This rewrite keeps the exact same features
but breaks the workflow into tiny helpers that read from top to bottom:

1. Parse the request and figure out the intent.
2. Load persona information and the most relevant market context.
3. Ask the language model for an answer.
4. Save the updated conversation state.

Every helper explains *why* it exists which should make the module accessible to
junior engineers or even curious students.
"""

from __future__ import annotations

import logging
import os
import re
import uuid
from datetime import datetime, timedelta
from typing import Annotated, Dict, List, Optional, Set, Tuple, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from app.services.guru_service import build_system_prompt
from app.services.kiwoom_client import KiwoomClient
from app.services.news_service import summarize_news
from app.services.rag_loader import (
    load_latest_summary,
    load_persona_chunks,
    pick_persona_for_intent,
)
from app.services.sector import format_output_html
from app.services.symbol_resolver import resolve_symbols_from_text

logger = logging.getLogger(__name__)

# --- basic configuration ----------------------------------------------------

CODE_RE = re.compile(r"\b\d{6}\b")
LIVE_KEYWORDS = {"실시간", "지금", "업데이트", "최신", "refresh", "update", "live", "real-time"}
NUMERIC_KEYWORDS = {
    "per",
    "pbr",
    "eps",
    "bps",
    "배당",
    "배당수익률",
    "밸류에이션",
    "52주",
    "등락률",
    "거래량",
    "거래대금",
    "지표",
    "재무",
}
PRICE_KEYWORDS = {"현재가", "주가", "시세", "가격", "호가"}
ANALYSIS_KEYWORDS = {"인사이트", "분석", "평가", "의견", "생각", "어떻게", "어떤", "판단", "전망", "전망해", "분석해", "평가해", "추천", "도출"}
METRIC_KEYWORDS = {
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
}
FORCE_LIVE = os.getenv("FORCE_LIVE", "").lower() in {"1", "true", "yes"}

METRIC_LABELS = {
    "CUR": "현재가",
    "PER": "PER",
    "PBR": "PBR",
    "EPS": "EPS",
    "BPS": "BPS",
    "DIV_YIELD": "배당수익률",
    "MKT_CAP": "시가총액",
    "52W_H": "52주 최고가",
    "52W_L": "52주 최저가",
    "CHG_RT": "등락률",
    "VOL": "거래량",
    "TRADE_VALUE": "거래대금",
}
METRIC_DISPLAY_ORDER = [
    "CUR",
    "PER",
    "PBR",
    "EPS",
    "BPS",
    "DIV_YIELD",
    "MKT_CAP",
    "52W_H",
    "52W_L",
    "CHG_RT",
    "VOL",
    "TRADE_VALUE",
]

llm = ChatOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    model_name=os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o-mini"),
    temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.3")),
)


class State(TypedDict):
    """Structure stored for each conversation session."""

    messages: Annotated[List, add_messages]


def _chatbot_step(state: State) -> Dict[str, List]:
    """Single node used by ``langgraph`` to query the language model."""

    response = llm.invoke(state["messages"])
    return {"messages": [response]}


workflow = StateGraph(State)
workflow.add_node("chatbot", _chatbot_step)
workflow.add_edge(START, "chatbot")
workflow.add_edge("chatbot", END)
chat_graph = workflow.compile()


class SessionStore:
    """Tiny in-memory session manager.

    The store intentionally avoids clever caching tricks: it simply keeps the
    sequence of messages for every session id so we can rebuild the conversation
    history on each turn.
    """

    def __init__(self) -> None:
        self._states: Dict[str, State] = {}

    def get(self, session_id: Optional[str]) -> Tuple[str, State]:
        if session_id and session_id in self._states:
            logger.debug("reuse session %s", session_id)
            return session_id, self._states[session_id]

        new_session_id = str(uuid.uuid4())
        self._states[new_session_id] = {"messages": []}
        logger.debug("created new session %s", new_session_id)
        return new_session_id, self._states[new_session_id]

    def save(self, session_id: str, state: State) -> None:
        self._states[session_id] = state

    def reset(self, session_id: Optional[str]) -> str:
        if session_id and session_id in self._states:
            del self._states[session_id]
            return f"세션 {session_id}을(를) 새로 만들었어요."

        cleared = len(self._states)
        self._states.clear()
        return f"모든 세션 {cleared}개를 비웠어요."


_session_store = SessionStore()


def get_or_create_session(session_id: Optional[str] = None, guru_id: str = "buffett") -> Tuple[str, State]:
    """Return the stored state or create a fresh one.

    ``guru_id`` is unused but kept for backwards compatibility with existing
    callers.
    """

    return _session_store.get(session_id)


def reset_session(session_id: Optional[str] = None) -> str:
    """Clear a specific session or wipe the entire cache."""

    return _session_store.reset(session_id)


# --- input understanding ----------------------------------------------------


def _find_codes_with_regex(text: str) -> List[str]:
    return CODE_RE.findall(text or "") if text else []


def find_symbols(message: str) -> List[str]:
    """Try to infer stock codes mentioned in the message."""

    if not message:
        return []

    symbols = resolve_symbols_from_text(message) or []
    if symbols:
        return symbols

    fallback = _find_codes_with_regex(message)
    if fallback:
        logger.debug("symbol fallback via regex: %s", fallback)
    return fallback


def _infer_intent(message: str) -> str:
    lowered = (message or "").lower()
    
    # 뉴스 분석 요청 우선 확인 (인사보다 우선)
    # "다음 뉴스 내용을", "뉴스 내용을", "분석해줘" 같은 패턴이 있으면 뉴스 분석
    news_analysis_patterns = [
        "다음 뉴스", "뉴스 내용", "뉴스 분석", "분석해줘", "분석해", 
        "투자 관점", "섹터 이름", "반도체", "금융서비스", "유틸리티"
    ]
    if any(pattern in lowered for pattern in news_analysis_patterns):
        return "news_analysis"
    
    if any(keyword in lowered for keyword in ["뉴스", "정책", "headline", "news"]):
        return "news_analysis"
    
    # 인사/자기소개 질문 확인 (뉴스 분석이 아닐 때만)
    greeting_keywords = ["안녕", "누구", "소개", "이름", "hello", "hi", "who are you", "who are"]
    if any(keyword in lowered for keyword in greeting_keywords):
        return "greeting"
    if any(keyword in lowered for keyword in ["비교", "vs", "대비", "차이"]):
        return "company_query"  # 비교 질문도 company_query로 분류
    if any(keyword in lowered for keyword in ["회사", "종목", "티커", "코드", "005", "000"]):
        return "company_query"
    if any(keyword in lowered for keyword in PRICE_KEYWORDS) or any(keyword in lowered for keyword in NUMERIC_KEYWORDS):
        return "company_query"
    if any(keyword in lowered for keyword in ["철학", "원칙", "원리"]):
        return "principles"
    return "news_analysis"


def _is_comparison_request(message: str) -> bool:
    """비교 질문인지 확인"""
    lowered = (message or "").lower()
    comparison_keywords = ["비교", "vs", "대비", "차이", "랑", "와", "하고"]
    return any(keyword in lowered for keyword in comparison_keywords)


def _infer_audience(message: str) -> str:
    lowered = (message or "").lower()
    if any(keyword in lowered for keyword in ["초보", "처음", "쉬운", "간단"]):
        return "new_user"
    if any(keyword in lowered for keyword in ["상세", "깊게", "전문", "경험자"]):
        return "returning_user"
    return ""


def _mentions_live(message: str) -> bool:
    lowered = (message or "").lower()
    return any(keyword in lowered for keyword in LIVE_KEYWORDS)


def _mentions_numeric(message: str) -> bool:
    lowered = (message or "").lower()
    return any(keyword in lowered for keyword in NUMERIC_KEYWORDS)


def _mentions_price(message: str) -> bool:
    return any(keyword in (message or "") for keyword in PRICE_KEYWORDS)

def _wants_analysis(message: str) -> bool:
    """분석, 인사이트, 평가 등을 요청하는지 확인"""
    lowered = (message or "").lower()
    return any(keyword in lowered for keyword in ANALYSIS_KEYWORDS)


# --- context loading --------------------------------------------------------


def _load_persona(guru_id: str, intent: str, audience: str) -> List[Dict]:
    persona_chunks = load_persona_chunks(guru_id)
    return pick_persona_for_intent(persona_chunks, intent=intent, audience=audience)


def _load_cached_context(guru_id: str, symbols: List[str]) -> Optional[Dict]:
    if not symbols:
        return None
    try:
        return load_latest_summary(guru_id, symbols=symbols)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("cached context lookup failed: %s", exc)
        return None


def _normalise_live_snapshot(raw: Dict, symbol: str) -> Optional[Dict]:
    if not isinstance(raw, dict):
        logger.warning("live snapshot was not a dict: %s", type(raw))
        return None
    if raw.get("return_code") not in (0, "0", None):
        logger.warning("live snapshot error: %s %s", raw.get("return_code"), raw.get("return_msg"))
        return None

    def _to_float(value: object) -> Optional[float]:
        try:
            return float(str(value).replace(",", ""))
        except Exception:
            return None

    today = datetime.now().strftime("%Y-%m-%d")
    current_price = _to_float(raw.get("cur_prc"))
    volume = _to_float(raw.get("trde_qty"))
    trade_value = (current_price * volume) if (current_price is not None and volume is not None) else None

    metric_order = [
        ("per", "PER"),
        ("pbr", "PBR"),
        ("eps", "EPS"),
        ("bps", "BPS"),
        ("dvd_yld", "DIV_YIELD"),
        ("mac", "MKT_CAP"),
        ("oyr_hgst", "52W_H"),
        ("oyr_lwst", "52W_L"),
        ("flu_rt", "CHG_RT"),
    ]

    def _text_snippet() -> str:
        parts = []
        for raw_key, label in metric_order:
            value = raw.get(raw_key)
            if value in (None, "", "-"):
                continue
            parts.append(f"{label} {value}")
        if current_price is not None:
            if isinstance(current_price, (int, float)):
                parts.insert(0, f"현재가 {int(current_price):,}")
            else:
                parts.insert(0, f"현재가 {current_price}")
        if not parts:
            return f"{symbol} 실시간 스냅샷"
        return f"{symbol} 실시간 스냅샷: " + ", ".join(parts)

    # 52주 최저가 음수 처리 (절댓값 사용)
    oyr_lwst_raw = raw.get("oyr_lwst")
    oyr_lwst_value = _to_float(oyr_lwst_raw)
    if oyr_lwst_value is not None and oyr_lwst_value < 0:
        # 음수인 경우 절댓값 사용 (데이터 오류 가능성)
        oyr_lwst_value = abs(oyr_lwst_value)
        logger.warning("52주 최저가가 음수였습니다. 절댓값으로 변환: %s -> %s", oyr_lwst_raw, oyr_lwst_value)
    
    record = {
        "section": "market_update",
        "intent": ["news_analysis"],
        "audience": [""],
        "updated": raw.get("trd_dd") or today,
        "symbols": [symbol],
        "text": _text_snippet(),
        "metadata": {
            "source": "kiwoom/rest(live)",
            "api_id": "ka10001",
            "metrics": {
                "PER": _to_float(raw.get("per")),
                "PBR": _to_float(raw.get("pbr")),
                "BPS": _to_float(raw.get("bps")),
                "EPS": _to_float(raw.get("eps")),
                "DIV_YIELD": _to_float(raw.get("dvd_yld") or raw.get("div_yield")),
                "MKT_CAP": _to_float(raw.get("mac")),
                "52W_H": _to_float(raw.get("oyr_hgst")),
                "52W_L": oyr_lwst_value,  # 음수 처리된 값 사용
                "CHG_RT": _to_float(raw.get("flu_rt")),
                "VOL": volume,
                "TRADE_VALUE": trade_value,
                "CUR": current_price,
            },
        },
    }

    try:
        date_str = str(record["updated"]).replace(".", "").replace("-", "")
        if len(date_str) == 8:
            record["updated"] = datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d")
        else:
            record["updated"] = str(record["updated"])[:10]
    except Exception:
        record["updated"] = today

    return record


async def _load_live_context(symbol: str) -> Optional[Dict]:
    logger.debug("calling kiwoom ka10001 for %s", symbol)
    client = KiwoomClient()
    try:
        raw = await client.ka10001(symbol)
    finally:
        await client.close()
    snapshot = _normalise_live_snapshot(raw, symbol)
    if snapshot:
        logger.debug("live snapshot ready for %s", symbol)
    else:
        logger.debug("live snapshot missing for %s", symbol)
    return snapshot


async def _load_multiple_live_contexts(symbols: List[str]) -> List[Dict]:
    """여러 종목의 실시간 지표를 가져옵니다."""
    contexts = []
    client = KiwoomClient()
    try:
        for symbol in symbols:
            try:
                raw = await client.ka10001(symbol)
                snapshot = _normalise_live_snapshot(raw, symbol)
                if snapshot:
                    contexts.append(snapshot)
            except Exception as exc:
                logger.warning("Failed to load live context for %s: %s", symbol, exc)
    finally:
        await client.close()
    return contexts


def _should_use_live(symbols: List[str], wants_live: bool, wants_price: bool, wants_numeric: bool, cached: Optional[Dict]) -> bool:
    if FORCE_LIVE:
        return True
    if not symbols:
        return False
    if wants_live or wants_price or wants_numeric:
        return True
    if not cached:
        return True
    try:
        updated = cached.get("updated") if isinstance(cached, dict) else None
        if updated:
            date_value = datetime.strptime(str(updated)[:10], "%Y-%m-%d")
            return datetime.now() - date_value > timedelta(days=7)
    except Exception:
        return False
    return False


def _compose_system_prompt(
    guru_id: str,
    intent: str,
    audience: str,
    persona: List[Dict],
    context_row: Optional[Dict],
    user_message: str,
    requested_metrics: Optional[Set[str]] = None,
    wants_all_metrics: bool = False,
    wants_analysis: bool = False,
    is_comparison: bool = False,
) -> str:
    system_prompt = build_system_prompt(persona, context_row, audience=audience, guru_id=guru_id)
    lowered = (user_message or "").lower()
    
    # 답변 길이 제한 (모든 답변에 적용)
    system_prompt += "\n답변 형식:\n"
    system_prompt += "- 답변은 반드시 3문장 이하로 간결하게 작성하세요.\n"
    system_prompt += "- 직관적이고 이해하기 쉬운 말을 사용하세요.\n"
    
    # 분석 요청 + 지표 질문 시 지표 명시적으로 포함
    if wants_analysis and context_row:
        if "multiple_companies" in context_row:
            # 비교 질문: 여러 종목의 지표 포함
            companies = context_row.get("multiple_companies", [])
            if companies:
                system_prompt += "\n비교 대상 종목의 실시간 지표:\n"
                for company in companies:
                    symbol = company.get("symbols", [""])[0] if company.get("symbols") else ""
                    company_metrics = (company.get("metadata") or {}).get("metrics") or {}
                    if company_metrics:
                        system_prompt += f"\n[{symbol}]:\n"
                        for key in METRIC_DISPLAY_ORDER:
                            if key in company_metrics:
                                value = _format_metric_value(key, company_metrics.get(key))
                                if value is not None:
                                    label = METRIC_LABELS.get(key, key)
                                    system_prompt += f"  - {label}: {value}\n"
                system_prompt += "\n위 지표를 바탕으로 비교 분석하고 매수 의견을 도출하세요.\n"
        else:
            # 단일 종목: 지표 포함 (분석 요청 시 또는 재무지표 질문 시)
            company_metrics = ((context_row or {}).get("metadata") or {}).get("metrics") or {}
            if company_metrics:
                # 분석 요청이거나 재무지표 관련 질문이면 지표 포함
                is_metric_request = requested_metrics or wants_all_metrics or "재무" in lowered or "지표" in lowered
                if wants_analysis or is_metric_request:
                    system_prompt += "\n요청하신 종목의 실시간 지표:\n"
                    if wants_all_metrics or (wants_analysis and not requested_metrics):
                        # 모든 지표 요청 또는 분석 요청 시 모든 지표 포함
                        keys = [key for key in METRIC_DISPLAY_ORDER if key in company_metrics]
                    else:
                        # 특정 지표만 요청
                        keys = [key for key in METRIC_DISPLAY_ORDER if key in requested_metrics and key in company_metrics]
                    
                    for key in keys:
                        value = _format_metric_value(key, company_metrics.get(key))
                        if value is not None:
                            label = METRIC_LABELS.get(key, key)
                            system_prompt += f"  - {label}: {value}\n"
                    system_prompt += "\n위 지표를 바탕으로 분석하고 의견을 도출하세요. '지표 없음'이라고 답변하지 마세요.\n"
    
    # 일반 지표 질문 안내
    if find_symbols(user_message) or any(keyword in lowered for keyword in NUMERIC_KEYWORDS):
        system_prompt += (
            "\n지표 안내:\n"
            "- 사용자가 숫자를 물으면 최신 날짜와 출처(kiwoom/rest)를 붙여 1~2개의 수치만 간단히 전달한다."
        )
    
    return system_prompt


def _format_metric_value(key: str, value: Optional[float]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str) and value.strip().lower() in {"", "none", "nan", "-"}:
        return None
    if key in {"DIV_YIELD", "CHG_RT"}:
        return f"{value:.2f}%" if isinstance(value, (int, float)) else str(value)
    if key in {"VOL", "TRADE_VALUE", "MKT_CAP", "CUR", "52W_H", "52W_L", "BPS", "EPS"}:
        try:
            return f"{int(float(value)):,}"
        except Exception:
            return str(value)
    try:
        return f"{float(value):.2f}"
    except Exception:
        return str(value)


def _metrics_appendix(context_row: Optional[Dict]) -> str:
    """지표 부록 생성 - 주가 질문이 아닐 때만 사용"""
    if not context_row:
        return ""
    metrics = ((context_row.get("metadata") or {}).get("metrics") or {}) if isinstance(context_row, dict) else {}
    if not metrics:
        return ""

    # 핵심 지표만 선택적으로 표시 (과도한 정보 방지)
    priority_metrics = ["PER", "PBR", "EPS", "BPS", "DIV_YIELD", "MKT_CAP"]
    
    formatted_rows = []
    for key in priority_metrics:
        if key in METRIC_LABELS:
            value = _format_metric_value(key, metrics.get(key))
            if value is not None:
                formatted_rows.append(f"- {METRIC_LABELS[key]}: {value}")

    if not formatted_rows:
        return ""

    lines = ["[참고 지표]"]
    updated = context_row.get("updated") if isinstance(context_row, dict) else None
    if updated:
        lines.append(f"기준일: {updated}")
    
    lines.extend(formatted_rows)
    return "\n".join(lines)


SECTOR_KEYWORDS = [
    "반도체",
    "유틸리티",
    "금융서비스",
    "소프트웨어·서비스",
    "에너지",
    "소재",
    "자동차·부품",
    "통신서비스",
    "보험",
    "은행",
    "헬스케어 장비·서비스",
]


def _extract_sector_from_answer(answer: str) -> Optional[str]:
    """응답에서 섹터 키워드를 추출합니다.
    
    섹터 키워드는 대괄호 안에 있거나, 문장 내에 명시적으로 포함될 수 있습니다.
    더 긴 섹터 이름부터 매칭하여 정확도를 높입니다.
    """
    if not answer:
        return None
    
    # 섹터 키워드를 길이 순으로 정렬 (긴 것부터 매칭하여 "헬스케어 장비·서비스"가 "장비"보다 먼저 매칭되도록)
    sorted_sectors = sorted(SECTOR_KEYWORDS, key=len, reverse=True)
    
    # 대괄호 안의 섹터 추출 (예: "[반도체]", "섹터: [금융서비스]")
    bracket_pattern = r'\[([^\]]+)\]'
    bracket_matches = re.findall(bracket_pattern, answer)
    for match in bracket_matches:
        for sector in sorted_sectors:
            if sector in match:
                logger.info("Extracted sector from bracket: %s (matched in: %s)", sector, match)
                return sector
    
    # 직접 섹터 키워드 매칭 (응답 텍스트 전체에서 검색)
    for sector in sorted_sectors:
        # 섹터 이름이 응답에 포함되어 있는지 확인
        if sector in answer:
            logger.info("Extracted sector from text: %s", sector)
            return sector
    
    logger.debug("No sector found in answer: %s", answer[:100] + "..." if len(answer) > 100 else answer)
    return None


def _append_sector_widget(answer: str) -> str:
    """응답에 섹터 정보가 있으면 시총 상위 5개 기업 정보를 추가합니다."""
    if not answer:
        logger.warning("Answer is empty, cannot append sector widget")
        return answer
        
    logger.info("Checking for sector in answer (length: %d)", len(answer))
    # 응답의 첫 300자만 로그로 확인 (너무 길면 생략)
    answer_preview = answer[:300] + "..." if len(answer) > 300 else answer
    logger.debug("Answer content preview: %s", answer_preview)
    
    sector = _extract_sector_from_answer(answer)
    if not sector:
        logger.warning("No sector found in answer. Available sectors: %s", SECTOR_KEYWORDS)
        logger.debug("Full answer for debugging: %s", answer)
        return answer
    
    logger.info("Sector extracted successfully: %s", sector)
    
    try:
        sector_info = format_output_html(sector)
        if sector_info:
            logger.info("Successfully generated sector widget for sector: %s (HTML length: %d)", sector, len(sector_info))
            result = answer + f"\n\n{sector_info}"
            logger.info("Final answer length: %d (original: %d, added: %d)", len(result), len(answer), len(sector_info))
            return result
        else:
            logger.warning("Sector widget is empty for sector: %s (no companies found via pyKRX)", sector)
            return answer
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to append sector widget for sector %s: %s", sector, exc, exc_info=True)
        return answer


def _limit_response_length(response: str, max_lines: int = 3) -> str:
    """비기너를 위한 답변 길이 제한 (2-3줄 이하)"""
    if not response:
        return response
    
    # 줄바꿈으로 분리
    lines = response.split('\n')
    
    # 빈 줄 제거
    non_empty_lines = [line.strip() for line in lines if line.strip()]
    
    # 최대 줄 수만큼만 선택
    if len(non_empty_lines) > max_lines:
        # 첫 max_lines개 줄만 선택하고 마지막에 "..." 추가하지 않음 (자연스럽게)
        limited_lines = non_empty_lines[:max_lines]
        return '\n'.join(limited_lines)
    
    return response


def _remove_uncertain_endings(response: str) -> str:
    """답변 끝의 불확실한/조건부 표현 및 매수/매도 추천 제거"""
    if not response:
        return response
    
    import re
    # 문장 분리 (마침표, 물음표, 느낌표 기준)
    sentences = re.split(r'(?<=[.!?])\s+', response)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if len(sentences) <= 1:
        # 문장이 1개뿐이면 그대로 반환
        return response
    
    # 마지막 문장 확인
    last_sentence = sentences[-1].strip()
    
    # 불확실한/조건부 표현으로 시작하는지 확인
    uncertain_starters = [
        '하지만', '그러나', '다만', '그런데', '그렇지만',
        '그러므로', '그래서', '따라서',
    ]
    
    # 불확실한 표현이 포함되어 있는지 확인
    uncertain_phrases = [
        '고려해보세요', '생각해보세요', '판단하세요', '확인해보세요',
        '고려해보면', '생각해보면', '판단해보면', '확인해보면',
        '고려하세요', '생각하세요', '판단하세요', '확인하세요',
        '보세요', '참고하세요', '검토해보세요',
        '어떻게 보이는지', '어떻게 보이는지 고려', '어떻게 보이는지 생각',
        '결정하는 것이 좋', '판단하는 것이 좋', '고려하는 것이 좋',
    ]
    
    # 매수/매도 추천 표현
    trading_recommendations = [
        '매수하는 것이 좋', '매수하는게 좋', '매수하는 게 좋', '매수하세요', '매수하시길', '매수 권장',
        '매도하는 것이 좋', '매도하는게 좋', '매도하는 게 좋', '매도하세요', '매도하시길', '매도 권장',
        '구매하는 것이 좋', '구매하는게 좋', '구매하는 게 좋', '구매하세요', '구매하시길', '구매 권장',
        '판매하는 것이 좋', '판매하는게 좋', '판매하는 게 좋', '판매하세요', '판매하시길', '판매 권장',
        '투자하는 것이 좋', '투자하는게 좋', '투자하는 게 좋', '투자하세요', '투자하시길', '투자 권장',
        '지금 매수', '지금 매도', '지금 구매', '지금 판매', '지금 투자',
        '매수 추천', '매도 추천', '구매 추천', '판매 추천', '투자 추천',
    ]
    
    # 마지막 문장이 불확실한 표현으로 시작하거나 포함하는 경우 제거
    should_remove = False
    
    # 불확실한 표현으로 시작하는지 확인
    for starter in uncertain_starters:
        if last_sentence.startswith(starter):
            should_remove = True
            break
    
    # 불확실한 표현이 포함되어 있는지 확인
    if not should_remove:
        for phrase in uncertain_phrases:
            if phrase in last_sentence:
                should_remove = True
                break
    
    # 매수/매도 추천이 포함되어 있는지 확인
    if not should_remove:
        for phrase in trading_recommendations:
            if phrase in last_sentence:
                should_remove = True
                break
    
    if should_remove:
        # 마지막 문장 제거
        cleaned_sentences = sentences[:-1]
        if cleaned_sentences:
            return ' '.join(cleaned_sentences).strip()
        else:
            # 문장이 모두 제거되면 원본 반환
            return response
    
    return response


def _format_response_for_readability(response: str) -> str:
    """답변을 가독성 있게 포맷팅 (문단 자동 분리)"""
    if not response:
        return response
    
    # 이미 줄바꿈이 있는 경우 (예: 지표 목록, 섹터 위젯 등)는 그대로 유지
    if '\n\n' in response or response.count('\n') > 2:
        # 이미 포맷팅된 답변인 경우
        return response
    
    # 문장 분리 (마침표, 물음표, 느낌표 기준)
    import re
    # 문장 끝 구분자: 마침표, 물음표, 느낌표 다음 공백
    # 단, 숫자 뒤의 마침표는 제외 (예: "20.83", "PER 20.83", "103,100" 등)
    # 더 정확한 패턴: 마침표/물음표/느낌표 다음 공백이 있고, 그 다음이 한글이나 대문자로 시작
    # 숫자 뒤 마침표 제외: (?<!\.\d) - 마침표 앞에 숫자가 없어야 함
    pattern = r'(?<!\.\d)(?<=[.!?])\s+(?=[가-힣A-Z])'
    sentences = re.split(pattern, response)
    
    # 빈 문장 제거 및 공백 정리
    sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 1]
    
    # 문장이 너무 많이 분리된 경우 원본 반환 (분리 실패 가능성)
    if len(sentences) > 15:
        # 문장이 너무 많이 분리되면 원본 그대로 반환 (잘못된 분리)
        return response
    
    if len(sentences) <= 1:
        # 문장이 1개 이하면 그대로 반환
        return response
    
    # 문단 분리: 2-3문장마다 줄바꿈 추가
    paragraphs = []
    current_paragraph = []
    
    for i, sentence in enumerate(sentences):
        # 문장 정리 (앞뒤 공백 제거)
        sentence = sentence.strip()
        if not sentence:
            continue
        
        # 마침표 추가하지 않음 (원본 유지)
        current_paragraph.append(sentence)
        
        # 문단 분리 조건
        should_break = False
        
        # 3문장이 모이면 무조건 문단 분리
        if len(current_paragraph) >= 3:
            should_break = True
        # 2문장이 모였고 문장이 길면 문단 분리
        elif len(current_paragraph) >= 2:
            # 현재 문장의 길이 확인
            sentence_len = len(sentence)
            # 현재 문장이 35자 이상이면 문단 분리 (긴 문장은 독립적으로)
            if sentence_len > 35:
                should_break = True
            # 현재 문장이 20자 이상이고 다음 문장이 있으면 문단 분리
            elif sentence_len > 20 and i < len(sentences) - 1:
                should_break = True
        
        if should_break:
            # 문단 결합 (공백으로 연결)
            para_text = ' '.join(current_paragraph)
            paragraphs.append(para_text)
            current_paragraph = []
    
    # 남은 문장들 추가
    if current_paragraph:
        para_text = ' '.join(current_paragraph)
        paragraphs.append(para_text)
    
    # 문단이 1개뿐이면 원본 반환 (변경 불필요)
    if len(paragraphs) <= 1:
        return response
    
    # 문단 사이에 줄바꿈 2개 추가 (가독성을 위해)
    formatted = '\n\n'.join(paragraphs)
    
    return formatted


def _extract_metric_requests(message: str) -> Tuple[Set[str], bool]:
    """사용자가 요청한 재무 지표 목록과 전체 요청 여부를 반환"""
    text = (message or "").lower()
    requested: Set[str] = set()
    wants_all = False

    for keyword, metrics in METRIC_KEYWORDS.items():
        if keyword in text:
            requested.update(metrics)

    if "재무 지표" in text or "재무지표" in text:
        wants_all = True
    if "지표" in text and any(token in text for token in ["모두", "전부", "다", "전체", "또", "추가", "가져올수있는", "가져올 수 있는"]):
        wants_all = True
    if "다 가져" in text or "다 불러" in text or "전부 가져" in text:
        wants_all = True

    return requested, wants_all


def _guess_display_name(user_input: str, symbols: List[str], context_row: Optional[Dict]) -> str:
    """응답에 사용할 대상 이름 추론"""
    if symbols:
        return symbols[0]
    if isinstance(context_row, dict):
        ctx_symbols = context_row.get("symbols")
        if ctx_symbols:
            return ctx_symbols[0]
    tokens = (user_input or "").split()
    if tokens:
        return tokens[0]
    return "요청 종목"


# --- public helpers ---------------------------------------------------------


async def get_initial_message(guru_id: str) -> Dict[str, object]:
    """Return the intro text and starter news list for the landing screen."""

    intent = "news_analysis"
    audience = ""
    persona = _load_persona(guru_id, intent, audience)
    system_prompt = _compose_system_prompt(guru_id, intent, audience, persona, None, "")

    # 버핏의 경우 고정된 인사 메시지 사용 (원래 문장으로 복원)
    if guru_id.lower() in ["buffett", "warren_buffett"]:
        intro_text = "나는 오래 검증된 원칙을 따릅니다. 복잡함보다 단순함, 단기 이익보다 꾸준함을 중시합니다."
    else:
        try:
            response = llm.invoke(
                [
                    SystemMessage(content="너는 친절한 투자 멘토야."),
                    HumanMessage(
                        content=(
                            f"당신은 {guru_id}입니다.\n"
                            "다음 텍스트(투자 철학/톤 일부)를 3~5문장으로 쉽고 따뜻하게 소개해 주세요.\n\n"
                            f"{system_prompt}\n"
                        )
                    ),
                ]
            )
            intro_text = response.content if isinstance(response, (AIMessage, SystemMessage, HumanMessage)) else str(response)
        except Exception as exc:  # pragma: no cover - dependency fallback
            logger.warning("initial intro generation failed: %s", exc)
            intro_text = "나는 오래 검증된 원칙을 따릅니다. 복잡함보다 단순함, 단기 이익보다 꾸준함을 중시합니다."

    try:
        news_items = await summarize_news(guru_id)
        if not isinstance(news_items, list):
            logger.warning("summarize_news returned non-list type: %s", type(news_items))
            news_items = []
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("initial news fetch failed: %s", exc, exc_info=True)
        news_items = []

    return {"intro": intro_text, "news": news_items}


async def generate_response(
    user_input: str,
    session_id: Optional[str] = None,
    guru_id: str = "buffett",
    user_type: str = "auto",
) -> Tuple[str, str]:
    """Main entry point used by the API layer."""

    if not user_input:
        return "", session_id or ""

    session_id, state = get_or_create_session(session_id, guru_id)
    intent = _infer_intent(user_input)
    audience = _infer_audience(user_input)
    symbols = find_symbols(user_input)

    logger.debug("intent=%s audience=%s symbols=%s", intent, audience, symbols)

    persona = _load_persona(guru_id, intent, audience)
    
    # symbols가 있으면 해당 심볼의 컨텍스트를 로드
    cached_context = _load_cached_context(guru_id, symbols)
    
    # symbols가 없어도 최신 13F 포트폴리오 데이터를 로드 (뉴스 분석 등에 사용)
    # 13F 데이터를 우선적으로 로드하기 위해 load_profile_summary 사용
    if not cached_context:
        try:
            from app.services.rag_loader import load_profile_summary
            # 13F 포트폴리오 데이터를 우선적으로 로드
            cached_context = load_profile_summary(guru_id)
            if cached_context:
                section = cached_context.get("section", "unknown")
                logger.info("Loaded 13F profile summary for guru: %s (section: %s, updated: %s)", 
                           guru_id, section, cached_context.get("updated") or cached_context.get("period_end") or "unknown")
                logger.debug("13F summary content preview: %s", 
                           (cached_context.get("content") or cached_context.get("text") or "")[:200])
            else:
                # 13F가 없으면 일반 최신 요약 로드
                cached_context = load_latest_summary(guru_id, symbols=None)
                if cached_context:
                    logger.info("Loaded latest summary (non-13F) for guru: %s", guru_id)
                else:
                    logger.warning("No summary found for guru: %s", guru_id)
        except Exception as exc:
            logger.error("Failed to load 13F summary for guru %s: %s", guru_id, exc, exc_info=True)

    wants_live = _mentions_live(user_input)
    wants_price = _mentions_price(user_input)
    wants_numeric = _mentions_numeric(user_input)
    is_comparison = _is_comparison_request(user_input)
    wants_analysis = _wants_analysis(user_input)
    requested_metrics, wants_all_metrics = _extract_metric_requests(user_input)
    
    # 비교 질문이면 여러 종목의 실시간 지표 가져오기
    if is_comparison and len(symbols) > 1:
        use_live = True  # 비교 질문은 항상 실시간 지표 사용
        try:
            live_contexts = await _load_multiple_live_contexts(symbols)
            # 여러 종목의 지표를 하나의 컨텍스트로 합치기
            if live_contexts:
                context_row = {"multiple_companies": live_contexts}
                metrics = {}  # 여러 종목이므로 metrics는 빈 dict로 처리
            else:
                context_row = cached_context
                metrics = ((context_row or {}).get("metadata") or {}).get("metrics") or {}
        except Exception as exc:
            logger.warning("Failed to load multiple live contexts: %s", exc)
            context_row = cached_context
            metrics = ((context_row or {}).get("metadata") or {}).get("metrics") or {}
    else:
        # 일반 질문 처리
        use_live = _should_use_live(symbols, wants_live, wants_price, wants_numeric, cached_context)
        
        live_context = None
        if use_live and symbols:
            try:
                live_context = await _load_live_context(symbols[0])
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("live snapshot failed: %s", exc)
        
        context_row = live_context or cached_context
        metrics = ((context_row or {}).get("metadata") or {}).get("metrics") or {}
    
    metrics_note = _metrics_appendix(context_row)

    # 주가/지표 질문 처리 준비
    # 단, 분석/인사이트 요청이면 LLM에 위임
    wants_analysis = _wants_analysis(user_input)
    requested_metrics, wants_all_metrics = _extract_metric_requests(user_input)
    lowered_user = (user_input or "").lower()
    explicit_news_request = any(keyword in lowered_user for keyword in ["뉴스", "headline", "news"])

    if (
        context_row
        and metrics
        and (requested_metrics or wants_all_metrics)
        and intent == "company_query"
        and not wants_analysis
    ):
        available_keys = [key for key in METRIC_DISPLAY_ORDER if key in metrics]
        # "추가 지표", "가져올수있는" 같은 질문은 모든 지표 제공
        if wants_all_metrics or not requested_metrics:
            keys = available_keys
        else:
            keys = [key for key in METRIC_DISPLAY_ORDER if key in requested_metrics]
            extra_keys = [key for key in requested_metrics if key not in METRIC_DISPLAY_ORDER]
            keys.extend(extra_keys)

        formatted_metrics = []
        missing_labels = []
        for key in keys:
            label = METRIC_LABELS.get(key, key)
            formatted_value = _format_metric_value(key, metrics.get(key))
            if formatted_value is not None:
                formatted_metrics.append((label, formatted_value))
            else:
                missing_labels.append(label)

        display_name = _guess_display_name(user_input, symbols, context_row)
        meta_parts = []
        updated = context_row.get("updated") if isinstance(context_row, dict) else None
        source = ((context_row.get("metadata") or {}).get("source") if isinstance(context_row, dict) else None) or ""
        if updated:
            meta_parts.append(f"기준일 {updated}")
        if source:
            meta_parts.append(f"출처 {source}")
        meta_text = ", ".join(part for part in meta_parts if part)

        if formatted_metrics:
            if len(formatted_metrics) == 1:
                # 단일 지표: "현재 PER은 10.60입니다"
                label, value = formatted_metrics[0]
                answer = f"현재 {label}은 {value}입니다."
            else:
                # 여러 지표
                if wants_all_metrics:
                    # 모든 지표 요청 시: "PER 10.60, PBR 0.90, EPS 12,705, BPS 150,243, 시가총액 513,829 입니다"
                    parts = [f"{label} {value}" for label, value in formatted_metrics]
                    answer = f"{', '.join(parts)} 입니다."
                else:
                    # 특정 지표 요청 시: "현재 PER은 10.60, PBR은 0.90입니다"
                    parts = [f"{label}은 {value}" for label, value in formatted_metrics]
                    answer = f"현재 {', '.join(parts)}입니다."
            if missing_labels:
                answer += f"\n(다음 지표는 제공되지 않습니다: {', '.join(missing_labels)})"
        else:
            # 지표가 없을 때는 LLM에 위임
            pass

        if audience == "new_user":
            answer = _limit_response_length(answer, max_lines=3)

        return answer.strip(), session_id
    
    if wants_price and context_row and not wants_analysis:
        # 단순 주가 질문만 간단히 답변
        price = metrics.get("CUR")
        
        if price is not None:
            try:
                pretty_price = f"{int(price):,}"
            except Exception:
                pretty_price = str(price)
            
            # 종목코드와 괄호 제거, 간단한 형식만
            answer = f"현재가는 {pretty_price}원입니다."
            
            return answer.strip(), session_id

    # 인사/자기소개 질문 처리
    if intent == "greeting":
        # 간단한 인사 답변 생성 (LLM에 위임하지 않고 직접 생성)
        # 버핏의 경우 할아버지 말투로
        if guru_id.lower() in ["buffett", "warren_buffett"]:
            answer = "안녕, 나는 워렌 버핏이란다."
        # 린치의 경우 신사 말투로
        elif guru_id.lower() in ["lynch", "peter_lynch"]:
            answer = "안녕하세요, 저는 피터 린치입니다."
        # 캐시우드의 경우 까칠한 말투로
        elif guru_id.lower() in ["wood", "cathie_wood"]:
            answer = "안녕, 나는 캐시 우드야."
        else:
            answer = "안녕하세요, 저는 투자 멘토입니다."
        
        return answer.strip(), session_id

    system_prompt = _compose_system_prompt(
        guru_id, intent, audience, persona, context_row, user_input,
        requested_metrics=requested_metrics,
        wants_all_metrics=wants_all_metrics,
        wants_analysis=wants_analysis,
        is_comparison=is_comparison
    )

    if not state["messages"] or not isinstance(state["messages"][0], SystemMessage):
        state["messages"].insert(0, SystemMessage(content=system_prompt))
    else:
        state["messages"][0] = SystemMessage(content=system_prompt)

    state["messages"].append(HumanMessage(content=user_input))

    result = chat_graph.invoke({"messages": state["messages"]})
    last_message = result["messages"][-1]
    if isinstance(last_message, (AIMessage, SystemMessage, HumanMessage)):
        ai_response = last_message.content
    else:  # pragma: no cover - safety
        ai_response = str(last_message)

    # 불확실한 마무리 제거 (모든 사용자에게 적용)
    ai_response = _remove_uncertain_endings(ai_response)
    
    # 비기너(new_user)는 답변 본문을 2-3줄 이하로 제한 (섹터 위젯 추가 전에)
    if audience == "new_user":
        ai_response = _limit_response_length(ai_response, max_lines=3)
    else:
        # 일반 사용자: 가독성을 위해 문단 자동 분리
        ai_response = _format_response_for_readability(ai_response)

    # 섹터 위젯은 명시적으로 뉴스 분석을 요청한 경우에만 추가
    if intent == "news_analysis" and explicit_news_request:
        ai_response = _append_sector_widget(ai_response)

    # 뉴스 분석 및 섹터 추천에는 참고 지표를 표시하지 않음
    if wants_numeric and metrics_note and intent != "news_analysis":
        ai_response = f"{ai_response}\n\n{metrics_note}"

    state["messages"] = result["messages"]
    _session_store.save(session_id, state)
    return ai_response, session_id