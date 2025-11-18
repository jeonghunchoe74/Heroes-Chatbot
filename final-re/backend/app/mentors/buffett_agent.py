from __future__ import annotations

import logging
from typing import Iterable, Sequence

from app.mentors.types import StockMetrics
from app.services.llm_service import invoke_llm

logger = logging.getLogger(__name__)


def _display_name(entry: StockMetrics | None) -> str:
    if not entry:
        return ""
    return entry.name or entry.symbol or ""


def _collect(items: Sequence[object] | Iterable[object] | None, limit: int) -> list[object]:
    if not items:
        return []
    seq = list(items)
    return seq[:limit]


def _coerce(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _build_macro_section(rows: Sequence[object] | None) -> list[str]:
    rows = list(rows or [])
    if not rows:
        return []

    lines = ["\n[거시 데이터]"]
    for record in rows:
        if isinstance(record, str):
            cleaned = record.strip()
            if cleaned:
                lines.append(cleaned)
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
            summary = record.get("summary") or record.get("text") or ""
            if parts:
                lines.append(" ".join(p for p in parts if p))
            if summary:
                lines.append(f"요약: {summary}")
            continue
        lines.append(_coerce(record))

    lines.append("\n※ RAG 캐시 기준이며 최신 값과 차이가 있을 수 있음.")
    return lines


def _build_metrics_section(metrics: Sequence[StockMetrics] | None) -> list[str]:
    metrics = metrics or []
    if not metrics:
        return []

    lines = ["\n[실시간 종목 지표]"]
    for entry in metrics:
        parts: list[str] = []
        name = entry.name or entry.symbol
        if name:
            parts.append(name)
        price = entry.price
        if price is not None:
            if isinstance(price, (int, float)):
                parts.append(f"현재가 {price:,.0f}원")
            else:
                parts.append(f"현재가 {price}")
        if entry.pe is not None:
            parts.append(f"PER {entry.pe}")
        if entry.pb is not None:
            parts.append(f"PBR {entry.pb}")
        if entry.div_yield is not None:
            parts.append(f"배당수익률 {entry.div_yield}%")
        if entry.roe is not None:
            parts.append(f"ROE {entry.roe}%")
        if parts:
            lines.append(" · ".join(parts))
    return lines


class BuffettAgent:
    """워런 버핏 멘토"""

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
        system_parts = [
            "나는 워런 버핏이다. 호들갑 떨지 말고, 모르면 모른다고 말한다.",
            "답변은 4~5문장(5~6줄) 이내로 간결히 정리하고 조언하듯 담담한 톤을 유지하라.",
        ]

        first_line = None
        primary = stock_metrics[0] if stock_metrics else None
        if primary and primary.price is not None:
            price_text = (
                f"{primary.price:,.0f}원" if isinstance(primary.price, (int, float)) else str(primary.price)
            )
            first_line = f"{_display_name(primary)} 현재가는 {price_text}입니다."

        if intent == "company_metrics":
            if stock_metrics:
                if first_line:
                    system_parts.append(f"첫 문장은 \"{first_line}\"으로 시작하라.")
                system_parts.append(
                    "PER·PBR·배당수익률·ROE를 역사적 평균과 비교해서 안전마진 여부를 한두 문장으로 정리하라."
                )
            else:
                system_parts.append("실시간 지표를 불러오지 못했다면 그 사실을 분명히 알려라.")
            if macro_data:
                system_parts.append("거시 지표가 있다면 금리·물가가 밸류에이션에 주는 압력을 한 문장으로 연결하라.")
                system_parts.extend(_build_macro_section(macro_data))

        elif intent == "company_analysis":
            system_parts.append("기업의 경쟁우위와 밸류에이션을 장기 관점에서 평가하라.")
            if first_line:
                system_parts.append(f"가능하면 \"{first_line}\"으로 답변을 시작하라.")
            if stock_metrics and primary:
                metrics_summary: list[str] = []

                def _fmt_value(val: object, digits: int = 2) -> str:
                    if isinstance(val, (int, float)):
                        if digits == 0:
                            return f"{val:,.0f}"
                        return f"{val:,.{digits}f}"
                    return str(val)

                if primary.pe is not None:
                    metrics_summary.append(f"PER {_fmt_value(primary.pe)}")
                if primary.pb is not None:
                    metrics_summary.append(f"PBR {_fmt_value(primary.pb)}")
                if primary.roe is not None:
                    metrics_summary.append(f"ROE {_fmt_value(primary.roe)}%")
                if primary.div_yield is not None:
                    metrics_summary.append(f"배당수익률 {_fmt_value(primary.div_yield)}%")
                if primary.price is not None:
                    metrics_summary.append(f"현재가 {_fmt_value(primary.price, 0)}원")

                if metrics_summary:
                    system_parts.append(
                        "아래 실시간 지표 숫자를 그대로 언급하고 역사적 평균 대비 안전마진을 판단하라: "
                        + ", ".join(metrics_summary)
                    )
            if philosophy_snippets:
                system_parts.append("\n[버핏 발언 참고]")
                for snippet in _collect(philosophy_snippets, 3):
                    system_parts.append(f"- {snippet[:300]}")
            if portfolio_history:
                system_parts.append("\n[포트폴리오 히스토리]")
                for record in _collect(portfolio_history, 2):
                    system_parts.append(f"- {record[:300]}")
            if macro_data:
                system_parts.append("거시 환경이 사업과 평가에 주는 함의를 간단히 언급하라.")
                system_parts.extend(_build_macro_section(macro_data))

        elif intent == "compare_companies":
            system_parts.append("두 종목의 가치와 사업 모델을 명확히 비교하라.")

        elif intent == "macro_outlook":
            system_parts.append("금리·물가·성장률이 투자자에게 주는 시그널을 요약하라.")
            system_parts.extend(_build_macro_section(macro_data))

        elif intent == "historical_data":
            system_parts.append("포트폴리오 히스토리를 근거로 과거 사례를 설명하라.")
            if portfolio_history:
                for record in _collect(portfolio_history, 3):
                    system_parts.append(record[:500])
            else:
                system_parts.append("관련 히스토리 데이터가 없습니다.")

        elif intent == "philosophy":
            system_parts.append("버핏의 투자 철학을 설명하되 근거가 없으면 답하지 말라.")

        system_parts.extend(_build_metrics_section(stock_metrics))
        system_prompt = "\n".join(system_parts)

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
            return response
        except Exception as exc:
            logger.error(f"LLM 호출 실패: {exc}", exc_info=True)
            return "죄송합니다. 응답을 생성하지 못했습니다."
