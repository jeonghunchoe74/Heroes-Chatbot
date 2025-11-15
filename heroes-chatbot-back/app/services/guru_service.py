# -*- coding: utf-8 -*-
from typing import List, Dict, Any, Tuple

def _txt(d: Dict[str, Any]) -> str:
    return (d.get("text") or d.get("content") or "").strip()

def _metric_pref_for(guru_id: str) -> List[str]:
    g = (guru_id or "").lower()
    if "buffett" in g:
        return ["PER","PBR","BPS","EPS","DIV_YIELD","MKT_CAP"]
    if "lynch" in g:
        return ["PER","EPS","52W_H","52W_L","CHG_RT","VOL"]
    if "wood" in g or "ark" in g:
        return ["MKT_CAP","TRADE_VALUE","VOL","CHG_RT","52W_H"]
    return ["PER","PBR","BPS","EPS","DIV_YIELD","MKT_CAP"]

def build_system_prompt(
    persona_chunks: List[Dict[str, Any]],
    latest_summary: Dict[str, Any] | None,
    audience: str = "",
    guru_id: str = "buffett",
) -> str:
    """Compose a compact natural language system prompt for the LLM."""

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

    sections.append(f"너는 {guru_id} 스타일의 투자 멘토야. 질문을 받으면 아래 원칙과 말투를 지켜라.")

    principles = _collect(("principles_core", "principles", "core"))
    if principles:
        sections.append("핵심 원칙:")
        sections.extend(principles)

    tone = _collect(("style_rules", "style_common", "tone_guide"))
    if tone:
        label = "말투 안내 (초보자)" if audience == "new_user" else (
            "말투 안내 (경험자)" if audience == "returning_user" else "말투 안내"
        )
        sections.append(label + ":")
        sections.extend(tone)

    safety = _collect(("safety", "do_dont"))
    if safety:
        sections.append("주의 사항:")
        sections.extend(safety)

    prefs = _metric_pref_for(guru_id)
    sections.append("지표 사용법:")
    sections.append("- 숫자는 1~2개만 예로 들고 과도하게 나열하지 않는다.")
    sections.append("- 수치가 없으면 '지표 없음'이라고 말하고 배경 설명을 덧붙인다.")
    sections.append(f"- 우선 참고 지표: {', '.join(prefs)}")
    sections.append("- 답변은 반드시 3문장 이하로 간결하게 작성한다.")
    sections.append("- 직관적이고 이해하기 쉬운 말을 사용한다.")
    sections.append("답변 마무리 규칙:")
    sections.append("- '하지만', '그러나', '다만', '그런데' 같은 조건부/애매한 말로 마무리하지 않는다.")
    sections.append("- '고려해보세요', '생각해보세요', '판단하세요' 같은 불확실한 표현을 피한다.")
    sections.append("- 확신 있는 답변으로 마무리한다. 예: 'PER이 20.83으로 적당한 수준이다.' 또는 '매출과 이익이 안정적으로 성장하고 있다.'")
    sections.append("- 조건부나 불확실한 말은 답변 중간에만 사용하고, 마지막 문장은 명확하고 확신 있게 끝낸다.")
    sections.append("매수/매도 추천 금지:")
    sections.append("- 절대 '매수하는 것이 좋습니다', '매도하세요', '지금 매수', '투자 권장' 같은 매수/매도 추천을 하지 않는다.")
    sections.append("- 종목 평가나 지표 설명만 하고, 구체적인 매수/매도 행동을 추천하지 않는다.")
    sections.append("- 예: 'PER이 20.83으로 적당한 수준이다.' (O) / '지금 매수하는 것이 좋습니다.' (X)")

    if latest_summary:
        tag = latest_summary.get("section", "summary")
        upd = latest_summary.get("updated") or latest_summary.get("period_end") or "unknown"
        text = _txt(latest_summary)
        
        # 13F 데이터인 경우 명시적으로 강조
        if tag == "13f_quarter_summary":
            sections.append("=== 현재 포트폴리오 정보 (13F 보고서 기반) ===")
            sections.append(f"기준일: {upd}")
            sections.append(f"포트폴리오 요약:\n{text}")
            sections.append("중요: 사용자가 포트폴리오, 보유 종목, 섹터 비중 등을 물어보면 위 정보를 반드시 참고하여 답변하세요.")
            sections.append("예를 들어 '가장 많이 보유한 주식'을 물어보면 위의 '상위 보유 Top5' 정보를 그대로 알려주세요.")
        else:
            sections.append("최신 데이터 요약:")
            sections.append(f"- ({tag} | 기준일 {upd}) {text}")
        
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
        # 디버깅: latest_summary가 None인 경우 로그
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("No latest_summary provided to build_system_prompt for guru: %s", guru_id)

    return "\n".join(sections)