# app/services/guru_service.py
from __future__ import annotations

import logging
from typing import List, Dict, Any, Tuple

from app.services.portfolio_service import load_portfolio, format_portfolio_text
from app.services.rag_loader import (
    load_persona_chunks,
    pick_persona_for_intent,
    load_latest_summary,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────
# 공통 헬퍼
# ─────────────────────────────

def _txt(d: Dict[str, Any]) -> str:
    """chunk / summary dict에서 텍스트만 깔끔하게 뽑기"""
    return (d.get("text") or d.get("content") or "").strip()


def _normalize_guru_id(guru_id: str | None) -> str:
    """멘토 id 정규화 (예전 코드와 호환)"""
    if not guru_id:
        return "buffett"

    g = guru_id.lower().strip()
    mapping = {
        # 캐시 우드
        "wood": "wood",
        "cathie": "wood",
        "ark": "wood",
        "cathie_wood": "wood",
        # 피터 린치
        "peter": "lynch",
        "peter_lynch": "lynch",
        # 워렌 버핏(확장)
        "warren": "buffett",
        "warren_buffett": "buffett",
    }
    return mapping.get(g, g)


def _metric_pref_for(guru_id: str) -> List[str]:
    """멘토별로 우선 보는 지표 세트"""
    g = (guru_id or "").lower()
    if "buffett" in g:
        return ["PER", "PBR", "BPS", "EPS", "DIV_YIELD", "MKT_CAP"]
    if "lynch" in g:
        return ["PER", "EPS", "52W_H", "52W_L", "CHG_RT", "VOL"]
    if "wood" in g or "ark" in g:
        return ["MKT_CAP", "TRADE_VALUE", "VOL", "CHG_RT", "52W_H"]
    return ["PER", "PBR", "BPS", "EPS", "DIV_YIELD", "MKT_CAP"]


# ─────────────────────────────
# 새 스타일: build_system_prompt
# (chatbot_service에서 직접 사용 중)
# ─────────────────────────────

def build_system_prompt(
    persona_chunks: List[Dict[str, Any]],
    latest_summary: Dict[str, Any] | None,
    audience: str = "",
    guru_id: str = "buffett",
) -> str:
    """RAG + 13F 요약을 섞어서 LLM 시스템 프롬프트 생성"""

    guru_id = _normalize_guru_id(guru_id)
    sections: List[str] = []

    def _collect(section_names: Tuple[str, ...]) -> List[str]:
        out: List[str] = []
        for chunk in persona_chunks or []:
            sec = str(chunk.get("section", "")).lower()
            if sec in section_names:
                text = _txt(chunk)
                if text:
                    out.append(f"- {text}")
        return out

    # 1) 기본 역할 정의
    sections.append(f"너는 {guru_id} 스타일의 투자 멘토야. 질문을 받으면 아래 원칙과 말투를 지켜라.")

    # 2) 투자 원칙
    principles = _collect(("principles_core", "principles", "core"))
    if principles:
        sections.append("핵심 원칙:")
        sections.extend(principles)

    # 3) 말투 / 대상자에 따른 톤
    tone = _collect(("style_rules", "style_common", "tone_guide"))
    if tone:
        label = (
            "말투 안내 (초보자)" if audience == "new_user"
            else "말투 안내 (경험자)" if audience == "returning_user"
            else "말투 안내"
        )
        sections.append(label + ":")
        sections.extend(tone)

    # 4) 안전 / 금지 사항
    safety = _collect(("safety", "do_dont"))
    if safety:
        sections.append("주의 사항:")
        sections.extend(safety)

    # 5) 지표 사용 가이드
    prefs = _metric_pref_for(guru_id)
    sections.append("지표 사용법:")
    sections.append("- 숫자는 1~2개만 예로 들고 과도하게 나열하지 않는다.")
    sections.append("- 수치가 없으면 '지표 없음'이라고 말하고 배경 설명을 덧붙인다.")
    sections.append(f"- 우선 참고 지표: {', '.join(prefs)}")
    sections.append("- 답변은 반드시 3문장 이하로 간결하게 작성한다.")
    sections.append("- 직관적이고 이해하기 쉬운 말을 사용한다.")

    # 6) 답변 마무리 규칙 / 매수·매도 금지
    sections.append("답변 마무리 규칙:")
    sections.append("- '하지만', '그러나', '다만', '그런데' 같은 조건부/애매한 말로 마무리하지 않는다.")
    sections.append("- '고려해보세요', '생각해보세요', '판단하세요' 같은 불확실한 표현을 피한다.")
    sections.append(
        "- 확신 있는 답변으로 마무리한다. 예: 'PER이 20.83으로 적당한 수준이다.' "
        "또는 '매출과 이익이 안정적으로 성장하고 있다.'"
    )
    sections.append("- 조건부나 불확실한 말은 답변 중간에만 사용하고, 마지막 문장은 명확하고 확신 있게 끝낸다.")
    sections.append("매수/매도 추천 금지:")
    sections.append("- 절대 '매수하는 것이 좋습니다', '매도하세요', '지금 매수', '투자 권장' 같은 매수/매도 추천을 하지 않는다.")
    sections.append("- 종목 평가나 지표 설명만 하고, 구체적인 매수/매도 행동을 추천하지 않는다.")
    sections.append("- 예: 'PER이 20.83으로 적당한 수준이다.' (O) / '지금 매수하는 것이 좋습니다.' (X)")

    # 7) 최신 요약(13F/기타) 붙이기
    if latest_summary:
        tag = latest_summary.get("section", "summary")
        upd = latest_summary.get("updated") or latest_summary.get("period_end") or "unknown"
        text = _txt(latest_summary)

        if tag == "13f_quarter_summary":
            sections.append("=== 현재 포트폴리오 정보 (13F 보고서 기반) ===")
            sections.append(f"기준일: {upd}")
            sections.append(f"포트폴리오 요약:\n{text}")
            sections.append(
                "중요: 사용자가 포트폴리오, 보유 종목, 섹터 비중 등을 물어보면 "
                "위 정보를 반드시 참고하여 답변하세요."
            )
            sections.append(
                "예를 들어 '가장 많이 보유한 주식'을 물어보면 위의 '상위 보유 Top5' 정보를 그대로 알려주세요."
            )
        else:
            sections.append("최신 데이터 요약:")
            sections.append(f"- ({tag} | 기준일 {upd}) {text}")

        # 선호 지표만 숫자 첨부
        metrics = (latest_summary.get("metadata") or {}).get("metrics") or {}
        metric_lines = []
        for key in prefs:
            value = metrics.get(key)
            if value in (None, "", "nan"):
                continue
            metric_lines.append(f"  · {key}: {value}")
        if metric_lines:
            sections.append("- 활용 가능한 숫자:")
            sections.extend(metric_lines)
    else:
        logger.warning("No latest_summary provided to build_system_prompt for guru: %s", guru_id)

    return "\n".join(sections)


# ─────────────────────────────
# 예전 스타일: get_guru_prompt
#  - 여전히 사용하는 코드가 있어서 유지
#  - 내부적으로는 위의 build_system_prompt를 재사용
# ─────────────────────────────

def _render_persona_block(chunks: List[Dict[str, Any]]) -> str:
    """옛 버전에서 쓰던 persona 블록 렌더링 (필요 시 재사용)"""
    if not chunks:
        return ""
    lines: List[str] = ["[Persona / Tone]"]
    for chunk in chunks:
        section = str(chunk.get("section", "section"))
        content = str(chunk.get("content", "")).strip()
        lines.append(f"({section}) {content}")
    return "\n".join(lines)


def _render_summary_block(summary: Dict[str, Any] | None) -> str:
    """옛 버전의 13F summary 블록 (지금은 참고용)"""
    if not summary:
        return ""
    updated = summary.get("updated") or summary.get("period_end") or ""
    content = str(summary.get("content", "")).strip()
    return f"[13F Summary]\n(기준일: {updated})\n{content}"


def get_guru_prompt(
    guru_id: str,
    intent: str = "news_analysis",
    audience: str = "",
) -> str:
    """
    (레거시용) RAG + 13F + 포트폴리오를 한 번에 불러서
    시스템 프롬프트 텍스트로 만들어 주는 함수.

    - 새 코드에서는 보통:
        persona_chunks, latest = ...  →  build_system_prompt(...)
      를 직접 쓰고,
    - 예전 라우터/실험 코드에서는 아직 이 함수를 부를 수 있음.
    """
    normalized_id = _normalize_guru_id(guru_id)

    # 1) RAG persona / summary 로드
    persona_chunks = load_persona_chunks(normalized_id)
    picked_chunks = pick_persona_for_intent(
        persona_chunks,
        intent=intent,
        audience=audience,
    )
    latest_summary = load_latest_summary(normalized_id)

    # 2) 업그레이드된 시스템 프롬프트 생성 (한국어 버전)
    base_prompt = build_system_prompt(
        persona_chunks=picked_chunks,
        latest_summary=latest_summary,
        audience=audience,
        guru_id=normalized_id,
    )

    # 3) 포트폴리오 스냅샷 추가 (예전 get_guru_prompt가 하던 역할)
    df = load_portfolio(normalized_id)
    portfolio_block = format_portfolio_text(df)

    parts: List[str] = [base_prompt]

    if portfolio_block:
        parts.append(f"[Portfolio Snapshot]\n{portfolio_block}")

    # 예전 끝문장 유지 (매수/매도 지시 금지 안내)
    parts.append("※ 종목 매수/매도 지시는 금지, 섹터 수준으로만 의견을 제시하세요.")

    # 완성
    return "\n\n".join(part for part in parts if part.strip())
