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

    lines = ["\n[매크로 데이터]"]
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
        if entry.price is not None:
            price_text = (
                f"{entry.price:,.0f}원" if isinstance(entry.price, (int, float)) else str(entry.price)
            )
            parts.append(f"현재가 {price_text}")
        if entry.peg is not None:
            parts.append(f"PEG {entry.peg:.2f}")
        if entry.eps_growth_percent is not None:
            parts.append(f"EPS 성장률 {entry.eps_growth_percent:.1f}%")
        if entry.pe is not None:
            parts.append(f"PER {entry.pe}")
        if entry.pb is not None:
            parts.append(f"PBR {entry.pb}")
        if parts:
            lines.append(" · ".join(parts))
    return lines


class LynchAgent:
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
            "나는 피터 린치다. 현실에서 얻은 관찰을 솔직하게 전한다.",
            "근거가 없으면 모른다고 말한다.",
            "답변은 4~5문장(5~6줄) 이내로 가볍게 정리하고, PEG·EPS 성장률을 중심으로 판단하라.",
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
                    "PEG와 최근 EPS 성장률이 있으면 PER과 연결해 성장 대비 밸류에이션을 한두 문장으로 설명하라."
                )
                system_parts.append("PEG가 없다면 성장률·재고·부채 추세로 성장성을 말하고 PER/PBR은 참고로만 언급하라.")
            else:
                system_parts.append("실시간 지표를 불러오지 못했다면 그 사실을 알려라.")
            if macro_data:
                system_parts.append("거시 지표가 있다면 개인 투자자가 체감할만한 경기 흐름을 한 문장으로 덧붙여라.")
                system_parts.extend(_build_macro_section(macro_data))

        elif intent == "company_analysis":
            system_parts.append("기업의 성장 스토리와 PEG 관점을 짧게 정리하라.")
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

                if primary.peg is not None:
                    metrics_summary.append(f"PEG {_fmt_value(primary.peg)}")
                if primary.eps_growth_percent is not None:
                    metrics_summary.append(f"EPS 성장률 {_fmt_value(primary.eps_growth_percent, 1)}%")
                if primary.pe is not None:
                    metrics_summary.append(f"PER {_fmt_value(primary.pe)}")
                if primary.pb is not None:
                    metrics_summary.append(f"PBR {_fmt_value(primary.pb)}")
                if primary.price is not None:
                    metrics_summary.append(f"현재가 {_fmt_value(primary.price, 0)}원")

                if metrics_summary:
                    system_parts.append(
                        "아래 수치를 그대로 인용해 성장 대비 밸류에이션을 판단하라: " + ", ".join(metrics_summary)
                    )
            if philosophy_snippets:
                system_parts.append("\n[린치 투자 원칙]")
                for snippet in _collect(philosophy_snippets, 3):
                    system_parts.append(f"- {snippet[:300]}")
            if portfolio_history:
                system_parts.append("\n[과거 포트폴리오 변화]")
                for hist in _collect(portfolio_history, 2):
                    system_parts.append(f"- {hist[:300]}")
            if macro_data:
                system_parts.append("거시 환경이 소비·성장주에 주는 영향을 한 문장으로 첨언하라.")
                system_parts.extend(_build_macro_section(macro_data))

        elif intent == "compare_companies":
            system_parts.append("두 종목의 성장률·PEG·시장 점유율 관점을 비교하라.")

        elif intent == "macro_outlook":
            system_parts.append("거시 변수들이 개인 투자자에게 주는 시그널을 짧게 설명하라.")
            system_parts.extend(_build_macro_section(macro_data))

        elif intent == "historical_data":
            system_parts.append("포트폴리오 히스토리를 근거로 과거 사례를 설명하라.")
            if portfolio_history:
                for hist in _collect(portfolio_history, 3):
                    system_parts.append(hist[:500])
            else:
                system_parts.append("관련 히스토리 데이터가 없습니다.")

        elif intent == "philosophy":
            system_parts.append("린치의 투자 철학을 설명하되 근거가 없으면 답변하지 말라.")

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
                guru_id="lynch",
            )
            return response
        except Exception as exc:
            logger.error(f"LLM 호출 실패: {exc}", exc_info=True)
            return "죄송합니다. 응답을 생성하지 못했습니다."
