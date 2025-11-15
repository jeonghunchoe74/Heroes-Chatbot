# app/mentors/buffett_agent.py
"""
워렌 버핏 에이전트
"""

from __future__ import annotations

import logging
from itertools import islice
from typing import Any, Iterable, Sequence

from app.mentors.types import StockMetrics

logger = logging.getLogger(__name__)

MAX_ANALYSIS_SNIPPETS = 3
MAX_COMPARISON_SNIPPETS = 2
MAX_HISTORY_SNIPPETS = 5
MAX_MACRO_RECORDS = 6
MAX_PHILOSOPHY_SNIPPETS = 6

ANALYSIS_SNIPPET_LIMIT = 300
PHILOSOPHY_SNIPPET_LIMIT = 1000
HISTORY_SNIPPET_LIMIT = 2000


def _collect_items(items: Sequence[object] | Iterable[object] | None, limit: int | None) -> list[object]:
    """시퀀스/이터러블을 최대 limit 개수만큼 잘라낸다."""
    if not items:
        return []
    if limit is None:
        return list(items) if isinstance(items, Sequence) else list(items)
    if isinstance(items, Sequence):
        return list(items[:limit])
    return list(islice(items, limit))


def _coerce_text(value: object) -> str:
    """다양한 입력을 문자열로 정규화."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _prepare_snippet(value: object, limit: int) -> tuple[str, bool]:
    """문자열을 잘라내고 트리밍 여부를 함께 반환."""
    text = _coerce_text(value)
    if not text:
        return "", False
    truncated = len(text) > limit
    if truncated:
        text = text[:limit].rstrip()
    return text, truncated


def _append_bullet_snippets(
    parts: list[str],
    title: str,
    snippets: Sequence[object] | Iterable[object] | None,
    *,
    limit: int,
    max_items: int,
) -> None:
    rows: list[str] = []
    for raw in _collect_items(snippets, max_items):
        text, truncated = _prepare_snippet(raw, limit)
        if not text:
            continue
        rows.append(f"- {text}")
        if truncated:
            rows.append("   ... (하위 생략)")
    if rows:
        parts.append(f"\n[{title}]")
        parts.extend(rows)


def _build_philosophy_section(snippets: Sequence[str] | None) -> list[str]:
    lines = [
        "너는 버핏의 발언과 주주서한을 기반으로 철학을 설명해야 한다.",
        "중요: 아래 RAG 발췌문을 근거로 사용하고, 근거가 없으면 추측하지 말라.",
    ]
    limited = _collect_items(snippets, MAX_PHILOSOPHY_SNIPPETS)
    if not limited:
        lines.append("\n[알림] RAG 발췌문이 존재하지 않습니다.")
        lines.append("이 경우 '관련 RAG 자료가 없어 답변을 생성할 수 없습니다.'라고 명확히 안내하라.")
        return lines

    lines.append(f"\n=== 버핏 발언/요약 (최대 {len(limited)}개) ===")
    for idx, snippet in enumerate(limited, 1):
        text, truncated = _prepare_snippet(snippet, PHILOSOPHY_SNIPPET_LIMIT)
        if not text:
            continue
        lines.append(f"\n[발언 {idx}]")
        lines.append(text)
        if truncated:
            lines.append("   ... (하위 생략)")

    lines.append("\n=== 답변 가이드 ===")
    lines.extend(
        [
            "1. 각 발언에서 핵심이 되는 문장을 찾아라.",
            "2. '밸류에이션', 'inflation', '규제', '경기', '주주에게' 같은 키워드가 보이면 반드시 다뤄라.",
            "3. 발언 연도나 맥락을 찾아 짧게 설명하라.",
            "4. 강조한 원칙과 사례를 함께 연결하라.",
            "5. 근거가 부족하면 '관련 RAG 자료에서 해당 내용을 찾을 수 없습니다.'라고 밝혀라.",
            "6. '모르겠다'라는 표현 대신 핵심을 정리해 설명하라.",
        ]
    )
    return lines


def _build_history_section(history: Sequence[str] | None) -> list[str]:
    limited = _collect_items(history, MAX_HISTORY_SNIPPETS)
    if not limited:
        return [
            "\n[알림] 포트폴리오 히스토리 데이터가 존재하지 않습니다.",
            "이 경우 '관련 RAG 자료가 없어 답변을 생성할 수 없습니다.'라고 안내하라.",
        ]

    lines = [f"\n[RAG: 포트폴리오 히스토리 (최대 {len(limited)}개)]"]
    for idx, record in enumerate(limited, 1):
        text, truncated = _prepare_snippet(record, HISTORY_SNIPPET_LIMIT)
        if not text:
            continue
        lines.append(f"\n[포트폴리오 {idx}]")
        lines.append(text)
        if truncated:
            lines.append("   ... (하위 생략)")
    lines.append("\n※ 공개된 13F 기반 데이터이므로 최신 포트폴리오와 시차가 있을 수 있습니다.")
    return lines


def _build_macro_section(macro_rows: Sequence[object] | None) -> list[str]:
    limited = _collect_items(macro_rows, MAX_MACRO_RECORDS)
    if not limited:
        return []

    lines = ["\n[RAG: 매크로 데이터]"]
    for record in limited:
        if isinstance(record, str):
            lines.append(record)
            continue
        if isinstance(record, dict):
            period = record.get("period", "")
            base_rate = record.get("base_rate")
            cpi = record.get("cpi_yoy")
            gdp = record.get("gdp_growth")
            parts = [f"{period}:" if period else ""]
            if base_rate is not None:
                parts.append(f"기준금리 {base_rate}%")
            if cpi is not None:
                parts.append(f"물가 {cpi}%")
            if gdp is not None:
                parts.append(f"GDP {gdp}%")
            merged = " ".join(p for p in parts if p)
            if merged:
                lines.append(merged)
            summary = record.get("summary")
            if summary:
                lines.append("RAG-매크로 요약: " + summary)
            continue
        lines.append(_coerce_text(record))
    lines.append("\n※ 해당 데이터는 RAG 캐시 기준이므로 최신 지표와 차이가 있을 수 있습니다.")
    return lines

def _build_metrics_section(metrics_list: Sequence[StockMetrics] | None) -> list[str]:
    lines: list[str] = []
    if not metrics_list:
        return lines

    lines.append("\n[종목 지표]")
    for metrics in metrics_list:
        parts: list[str] = []
        if metrics.symbol:
            parts.append(f"{metrics.symbol}:")
        if metrics.price is not None:
            parts.append(f"현재가 {metrics.price}")
        if metrics.pe is not None:
            parts.append(f"PER {metrics.pe}")
        if metrics.pb is not None:
            parts.append(f"PBR {metrics.pb}")
        if metrics.roe is not None:
            parts.append(f"ROE {metrics.roe}%")
        if parts:
            lines.append(" ".join(parts))
    return lines


class BuffettAgent:
    """워렌 버핏 스타일의 투자 분석 에이전트"""

    async def generate_response(
        self,
        query: str,
        intent: str,
        symbols: Sequence[str],
        stock_metrics: Sequence[StockMetrics] | None = None,
        macro_data: Sequence[object] | None = None,
        philosophy_snippets: Sequence[str] | None = None,
        portfolio_history: Sequence[str] | None = None,
    ) -> str:
        """
        버핏 스타일로 응답 생성.

        Args:
            query: 사용자 질문
            intent: Intent 값
            symbols: 종목 심볼 리스트
            stock_metrics: 종목 지표 리스트
            macro_data: 매크로 데이터 리스트
            philosophy_snippets: 철학 스니펫 리스트
            portfolio_history: 포트폴리오 히스토리 리스트
        """
        from app.services.llm_service import invoke_llm

        system_parts = [
            "너는 워렌 버핏이다. 할아버지처럼 따뜻하고 편하게 말하라.",
            '말투: "~거야", "~지", "~란다" 같은 편안한 어투 사용.',
            "핵심 원칙: 장기 가치 투자, 안전마진, 사업의 본질 중시.",
            "아래 [RAG:*] 섹션의 근거를 반드시 인용하고, 원본에 없는 내용은 추측하지 말라.",
            "근거를 사용할 때 문장 안에 'RAG-철학', 'RAG-매크로'처럼 출처를 명시하라.",
        ]

        if intent == "company_metrics":
            if stock_metrics:
                system_parts.append("단순 지표 질문이므로, 아래 [종목 지표] 섹션의 Kiwoom에서 가져온 숫자만 간단히 알려주고 해석은 최소화하라.")
            else:
                system_parts.append("중요: 실시간 주가 조회에 실패했습니다. 주가나 지표 질문에는 '실시간 주가 조회에 실패했습니다. 잠시 후 다시 시도해주세요'라고 명확히 답하라. RAG 문서에서 주가를 찾으려고 시도하지 말라.")

        elif intent == "company_analysis":
            system_parts.append("종목을 장기 가치와 사업 본질 관점에서 평가하라.")
            _append_bullet_snippets(
                system_parts,
                "RAG: 버핏의 투자 원칙",
                philosophy_snippets,
                limit=ANALYSIS_SNIPPET_LIMIT,
                max_items=MAX_ANALYSIS_SNIPPETS,
            )
            _append_bullet_snippets(
                system_parts,
                "RAG: 과거 포트폴리오 변화",
                portfolio_history,
                limit=ANALYSIS_SNIPPET_LIMIT,
                max_items=2,
            )

        elif intent == "compare_companies":
            system_parts.append("두 종목을 장기 가치와 사업 모델 기준으로 비교하라.")
            _append_bullet_snippets(
                system_parts,
                "RAG: 비교 기준",
                philosophy_snippets,
                limit=ANALYSIS_SNIPPET_LIMIT,
                max_items=MAX_COMPARISON_SNIPPETS,
            )

        elif intent == "macro_outlook":
            system_parts.append("매크로 환경이 멘토의 투자 관점에 어떤 의미인지 요약하라.")
            system_parts.extend(_build_macro_section(macro_data))

        elif intent == "historical_data":
            system_parts.append("포트폴리오 히스토리에 관한 질문이므로 과거 데이터를 근거로 답하라.")
            system_parts.append("공개된 포트폴리오 데이터를 기반으로 했음을 명확히 알리고 최신 정보와 다를 수 있음을 강조하라.")
            system_parts.extend(_build_history_section(portfolio_history))

        elif intent == "philosophy":
            system_parts.extend(_build_philosophy_section(philosophy_snippets))

        system_parts.extend(_build_metrics_section(stock_metrics))
        system_prompt = "\n".join(system_parts)

        if intent == "philosophy":
            logger.info(
                "[BUFFETT_AGENT] Philosophy intent: %s snippets",
                len(philosophy_snippets) if philosophy_snippets else 0,
            )
            logger.debug(f"[BUFFETT_AGENT] System prompt length: {len(system_prompt)} chars")
            if philosophy_snippets:
                logger.debug(f"[BUFFETT_AGENT] First snippet preview: {philosophy_snippets[0][:200]}...")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]

        try:
            response = await invoke_llm(
                messages=messages,
                model_kind="mentor",
                guru_id="buffett",
            )

            if intent == "philosophy" and len(response.strip()) < 50:
                logger.warning(f"[BUFFETT_AGENT] Response too short: '{response}' (length={len(response)})")
                logger.warning(
                    "[BUFFETT_AGENT] Philosophy snippets count: %s",
                    len(philosophy_snippets) if philosophy_snippets else 0,
                )

            return response
        except Exception as exc:
            logger.error(f"LLM 호출 실패: {exc}", exc_info=True)
            return "죄송합니다. 응답 생성 중 오류가 발생했습니다."
