# app/mentors/lynch_agent.py
"""
피터 린치 에이전트
"""

from __future__ import annotations

import logging
from typing import List, Optional

from app.services.llm_service import invoke_llm

logger = logging.getLogger(__name__)


class LynchAgent:
    """피터 린치 스타일의 투자 분석 에이전트"""
    
    async def generate_response(
        self,
        query: str,
        intent: str,
        symbols: list[str],
        stock_metrics: list | None = None,
        macro_data: list | None = None,
        philosophy_snippets: list | None = None,
        portfolio_history: list | None = None,
    ) -> str:
        """린치 스타일로 응답 생성"""
        system_parts = [
            "너는 피터 린치다. 신사처럼 정중하고 예의 바르게 말하라.",
            "말투: \"~니다\", \"~습니다\", \"~세요\" 같은 정중한 어투 사용.",
            "핵심 원칙: 성장 투자, 소비자 접점, 스토리 중시.",
        ]
        
        if intent == "company_metrics":
            if stock_metrics:
                system_parts.append("단순 지표 질문이므로, 아래 [종목 지표] 섹션의 Kiwoom에서 가져온 숫자만 간단히 알려주고 해석은 최소화하라.")
            else:
                system_parts.append("중요: 실시간 주가 조회에 실패했습니다. 주가나 지표 질문에는 '실시간 주가 조회에 실패했습니다. 잠시 후 다시 시도해주세요'라고 명확히 답하라. RAG 문서에서 주가를 찾으려고 시도하지 말라.")
        
        elif intent == "company_analysis":
            system_parts.append("종목을 성장성, 스토리, 소비자 접점 관점에서 평가하라.")
            if philosophy_snippets:
                system_parts.append("\n[린치의 투자 원칙]")
                for snippet in philosophy_snippets[:3]:
                    system_parts.append(f"- {snippet[:300]}")
            if portfolio_history:
                system_parts.append("\n[과거 포트폴리오 사례]")
                for hist in portfolio_history[:2]:
                    system_parts.append(f"- {hist[:300]}")
        
        elif intent == "compare_companies":
            system_parts.append("두 종목을 성장성과 스토리 관점에서 비교하라.")
        
        elif intent == "macro_outlook":
            system_parts.append("매크로 환경이 투자자에게 어떤 영향을 미치는지 분석하라.")
            if macro_data:
                system_parts.append("\n[최근 매크로 데이터]")
                for record in macro_data:
                    if isinstance(record, str):
                        system_parts.append(record)
                        continue
                    if isinstance(record, dict):
                        period = record.get("period", "")
                        base_rate = record.get("base_rate")
                        cpi = record.get("cpi_yoy")
                        gdp = record.get("gdp_growth")
                        parts = [f"{period}:"]
                        if base_rate is not None:
                            parts.append(f"기준금리 {base_rate}%")
                        if cpi is not None:
                            parts.append(f"물가 {cpi}%")
                        if gdp is not None:
                            parts.append(f"GDP {gdp}%")
                        system_parts.append(" ".join(parts))
                        summary = record.get("summary")
                        if summary:
                            system_parts.append("요약: " + summary)
                        continue
                    system_parts.append(str(record))
                system_parts.append("\n해당 데이터는 RAG 기반 정보이므로 최신 값이 아닐 수 있습니다.")

        elif intent == "historical_data":
            system_parts.append("포트폴리오 히스토리나 과거 데이터에 대한 질문에 답하라.")
            system_parts.append("제공된 포트폴리오 데이터를 기반으로 정확한 정보를 제공하라.")
            if portfolio_history:
                system_parts.append(f"\n[포트폴리오 히스토리 (총 {len(portfolio_history)}개)]")
                for i, hist in enumerate(portfolio_history, 1):
                    system_parts.append(f"\n[포트폴리오 {i}]")
                    hist_text = hist[:2000] if len(hist) > 2000 else hist
                    system_parts.append(hist_text)
                    if len(hist) > 2000:
                        system_parts.append("   ... (이하 생략)")
                system_parts.append("\n※ 위 포트폴리오 데이터를 기반으로 정확한 정보를 제공하라.")
                system_parts.append("※ 가장 최신 포트폴리오를 우선적으로 참고하라.")
            else:
                system_parts.append("\n[주의] 포트폴리오 히스토리 데이터가 제공되지 않았습니다.")
        
        elif intent == "philosophy":
            system_parts.append("RAG에 있는 린치의 책/인터뷰 내용만 사용해서 답하라.")
            system_parts.append("RAG에 없는 내용은 상상하지 말고 '모르겠다'고 말해라.")
            if philosophy_snippets:
                system_parts.append("\n[린치의 원문/인용]")
                for snippet in philosophy_snippets:
                    system_parts.append(f"- {snippet[:500]}")
        
        if stock_metrics:
            system_parts.append("\n[종목 지표]")
            for metrics in stock_metrics:
                parts = [f"{metrics.symbol}:"]
                if hasattr(metrics, 'price') and metrics.price:
                    parts.append(f"현재가 {metrics.price}")
                if hasattr(metrics, 'pe') and metrics.pe:
                    parts.append(f"PER {metrics.pe}")
                if hasattr(metrics, 'pb') and metrics.pb:
                    parts.append(f"PBR {metrics.pb}")
                if hasattr(metrics, 'roe') and metrics.roe:
                    parts.append(f"ROE {metrics.roe}%")
                system_parts.append(" ".join(parts))
        
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
            return f"죄송합니다. 응답 생성 중 오류가 발생했습니다."

