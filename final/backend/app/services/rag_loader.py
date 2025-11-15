# -*- coding: utf-8 -*-
"""
RAG 로더 유틸리티 (통합 버전)

- app/data/prompts/<guru>.jsonl        → 투자 대가별 퍼소나 조각 로드
- app/data/summaries/<guru>_summaries.jsonl
- app/data/summaries/market.jsonl      → 시장/종목 요약 병합 후 최신 1건 선택

제공 함수:
- load_persona_chunks(guru_id)
- pick_persona_for_intent(chunks, intent, audience="")
- load_latest_summary(guru_id, symbols=None)
- load_profile_summary(guru_id)
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

# 프로젝트 루트(app/.. 의 부모) 기준으로 데이터 경로 설정
BASE_DIR = Path(__file__).resolve().parents[2]
PROMPTS_DIR = BASE_DIR / "app" / "data" / "prompts"
SUMMARIES_DIR = BASE_DIR / "app" / "data" / "summaries"

DATE_RX = re.compile(r"\b(20\d{2})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b")

# 포트폴리오/철학 관련 섹션 우선순위
PRIORITY_SECTIONS = {
    "portfolio",
    "holdings",
    "philosophy",
    "principles",
    "13f_quarter_summary",
}


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    """
    JSONL 파일을 안전하게 읽어 리스트로 반환.
    - 파일이 없거나 파싱 실패 시 빈 리스트를 돌려준다.
    - 로드된 행 수를 간단히 로그로 출력한다.
    """
    if not path.exists():
        print(f"[WARN] JSONL not found: {path}")
        return []

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        print(f"[ERROR] JSONL read failed: {path} -> {exc}")
        return []

    rows: List[Dict[str, Any]] = []
    for idx, raw in enumerate(text.splitlines(), start=1):
        line = raw.replace("\ufeff", "").strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception as exc:
            preview = (line[:80] + "...") if len(line) > 80 else line
            print(f"[WARN] JSONL parse skip {path.name}:{idx} -> {exc} | {preview}")
            continue

    if not rows:
        print(f"[WARN] JSONL empty after parsing: {path}")
    else:
        print(f"[LOAD] {path} rows={len(rows)}")
    return rows


def load_persona_chunks(guru_id: str) -> List[Dict[str, Any]]:
    """
    투자 대가별 퍼소나 조각(JSONL)을 로드한다.
    
    [DEPRECATED] 이 함수는 레거시 prompts 폴더를 사용합니다.
    새로운 RAG 구조에서는 app.services.rag_service.get_guru_philosophy_snippets()를 사용하세요.
    """
    # 레거시 prompts 폴더는 더 이상 사용하지 않음
    # 빈 리스트 반환하여 경고 방지
    return []


def pick_persona_for_intent(
    chunks: List[Dict[str, Any]],
    intent: str,
    audience: str = "",
) -> List[Dict[str, Any]]:
    """
    intent + audience 조건에 맞는 청크만 선별한다.

    - audience가 ''이면 공통/빈 audience 모두 허용
    - 보조 섹션: principles_core, style_rules, style_common, tone_guide 포함
    - 같은 section은 1개만 남긴다.
    """
    i = (intent or "").lower().strip()
    a = (audience or "").lower().strip()

    def intents_of(c: Dict[str, Any]) -> List[str]:
        iv = c.get("intent", [])
        if isinstance(iv, list):
            return [str(x).lower() for x in iv]
        return [str(iv).lower()] if iv else []

    # 1) intent 일치 (intent가 비어 있으면 전체 허용)
    main = [c for c in chunks if i in intents_of(c)] if i else list(chunks)

    # 2) audience 필터(빈값이면 모두 허용)
    def aud_ok(c: Dict[str, Any]) -> bool:
        aud = str(c.get("audience", "")).lower().strip()
        if not a:
            return True
        if not aud:
            return True
        return aud == a

    main = [c for c in main if aud_ok(c)]

    # 3) 보조 섹션
    helper_sections = {"principles_core", "style_rules", "style_common", "tone_guide"}
    helpers = [
        c
        for c in chunks
        if str(c.get("section", "")).lower() in helper_sections and aud_ok(c)
    ]

    # 4) 섹션별 1개만 선택
    picked: List[Dict[str, Any]] = []
    seen = set()
    for c in main + helpers:
        sec = c.get("section", "misc")
        if sec in seen:
            continue
        seen.add(sec)
        picked.append(c)
    return picked


def _to_date(val: Optional[str]) -> Optional[date]:
    if not val:
        return None
    try:
        y, m, d = str(val)[:10].split("-")
        return date(int(y), int(m), int(d))
    except Exception:
        return None


def _extract_date_from_text(text: str) -> Optional[date]:
    """
    content/text 안에 YYYY-MM-DD 패턴이 있으면 그 날짜를 추출한다.
    """
    if not text:
        return None
    m = DATE_RX.search(text)
    if not m:
        return None
    y, mo, d = m.group(1), m.group(2), m.group(3)
    try:
        return date(int(y), int(mo), int(d))
    except Exception:
        return None


def load_latest_summary(
    guru_id: str,
    symbols: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    summaries JSONL에서 최신 기록 1개를 반환한다.

    [DEPRECATED] 이 함수는 레거시 summaries 폴더를 사용합니다.
    새로운 RAG 구조에서는 app.services.rag_service를 사용하세요.
    """
    # 레거시 summaries 폴더는 더 이상 사용하지 않음
    return None


def load_profile_summary(guru_id: str) -> Optional[Dict[str, Any]]:
    """
    포트폴리오/철학(프로필성) 요약을 최신으로 1개 반환.

    [DEPRECATED] 이 함수는 레거시 summaries 폴더를 사용합니다.
    새로운 RAG 구조에서는 app.services.rag_service.get_portfolio_history_snippets()를 사용하세요.
    """
    # 레거시 summaries 폴더는 더 이상 사용하지 않음
    return None
