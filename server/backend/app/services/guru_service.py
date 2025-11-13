# app/services/guru_service.py
from typing import List, Dict, Any
from app.services.rag_loader import (
    load_persona_chunks,
    pick_persona_for_intent,
    load_latest_summary,
)

# 이 파일은 "System 프롬프트 만들기" 담당이에요.
# 퍼소나 조각(JSONL) + 최신 요약(JSONL)을 합쳐 깔끔한 문장으로 만듭니다.

def _normalize_guru_id(guru_id: str) -> str:
    g = (guru_id or "").strip().lower()
    if g in ["ark", "wood", "cathie", "cathie_wood"]:
        return "wood"
    if g in ["buffett", "warren", "berkshire", "berkshire_hathaway"]:
        return "buffett"
    if g in ["lynch", "peter", "peter_lynch"]:
        return "lynch"
    return g

def _render_persona_block(chunks: List[Dict[str, Any]]) -> str:
    if not chunks:
        return ""
    lines: List[str] = ["[규칙/템플릿/톤]"]
    for c in chunks:
        sec = str(c.get("section", "section"))
        content = str(c.get("content", "")).strip()
        lines.append(f"({sec}) {content}")
    return "\n".join(lines)

def _render_summary_block(row):
    if not row:
        return ""
    updated = row.get("updated") or row.get("period_end") or ""
    content = str(row.get("content","")).strip()
    return f"[요약]\n(기준일: {updated})\n{content}"

def get_guru_prompt(guru_id: str, intent: str = "news_analysis", audience: str = "") -> str:
    """
    1) 퍼소나 조각을 불러온다.
    2) intent + audience(신규/기존)에 맞는 것만 고른다.
    3) 최신 요약 1개를 붙인다.
    4) 간단한 안전 수칙을 덧붙인다.
    """
    gid = _normalize_guru_id(guru_id)

    # 퍼소나(규칙/톤/템플릿) 조각
    all_persona = load_persona_chunks(gid)
    picked = pick_persona_for_intent(all_persona, intent=intent, audience=audience)

    # 최신 요약 1개
    summary_row = load_latest_summary(gid)

    # 문장 조립 (아주 쉬운 문장 위주)
    parts: List[str] = []
    parts.append(f"You are acting as **{gid}** (교육용). Speak Korean politely.")

    # audience 힌트(모델이 톤을 잘 잡도록)
    if audience == "new_user":
        parts.append("초보자도 이해할 쉬운 표현을 사용하고, 2~3문장으로 간단히 설명하세요.")
    elif audience == "returning_user":
        parts.append("핵심 지표나 매크로 포인트를 근거로 2~3문장에 간결히 설명하세요.")

    # 규칙/템플릿/톤
    persona_block = _render_persona_block(picked)
    if persona_block:
        parts.append(persona_block)

    # 요약(13F 스냅샷)
    if summary_row:
        parts.append(_render_summary_block(summary_row))

    # 안전 수칙
    parts.append("※ 종목 추천/매수·매도 지시는 금지입니다. 섹터 수준으로만 이야기하세요.")

    return "\n\n".join([p for p in parts if p.strip()])
