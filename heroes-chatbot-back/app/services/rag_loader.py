# -*- coding: utf-8 -*-
"""
RAG 로더 (너의 스키마 호환 + market.jsonl 병합)
- app/data/prompts/<guru>.jsonl 에서 퍼소나 조각 로드
- app/data/summaries/<guru>_summaries.jsonl + app/data/summaries/market.jsonl 병합 후 최신 1건 선택
- 포트폴리오/철학 섹션 우선 로더(load_profile_summary) 추가
"""

import json
import re
from datetime import date
from pathlib import Path
from typing import List, Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parents[2]
PROMPTS_DIR = BASE_DIR / "app" / "data" / "prompts"
SUMMARIES_DIR = BASE_DIR / "app" / "data" / "summaries"

DATE_RX = re.compile(r"\b(20\d{2})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b")
PRIORITY_SECTIONS = {"portfolio", "holdings", "philosophy", "principles", "13f_quarter_summary"}

def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        print(f"[WARN] JSONL not found: {path}")
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"[ERROR] JSONL read failed: {path} -> {e}")
        return []
    rows: List[Dict[str, Any]] = []
    for idx, raw in enumerate(text.splitlines(), start=1):
        line = raw.replace("\ufeff", "").strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception as e:
            preview = (line[:80] + "...") if len(line) > 80 else line
            print(f"[WARN] JSONL parse skip {path.name}:{idx} -> {e} | {preview}")
            continue
    if not rows:
        print(f"[WARN] JSONL empty after parsing: {path}")
    print(f"[LOAD] {path} rows={len(rows)}")
    return rows

def load_persona_chunks(guru_id: str) -> List[Dict[str, Any]]:
    path = PROMPTS_DIR / f"{guru_id.lower()}.jsonl"
    return _read_jsonl(path)

def pick_persona_for_intent(chunks: List[Dict[str, Any]], intent: str, audience: str = "") -> List[Dict[str, Any]]:
    """
    intent + audience로 고르기
    - audience가 ''이면 모두 허용(공통도 허용)
    - 보조 섹션: principles_core, style_rules, style_common, tone_guide 추가
    - 섹션별 1개
    """
    i = (intent or "").lower().strip()
    a = (audience or "").lower().strip()

    def intents_of(c):
        iv = c.get("intent", [])
        if isinstance(iv, list):
            return [str(x).lower() for x in iv]
        return [str(iv).lower()] if iv else []

    # 1) intent 일치
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
    helpers = [c for c in chunks if str(c.get("section","")).lower() in helper_sections and aud_ok(c)]

    # 4) 섹션별 1개
    picked, seen = [], set()
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

def load_latest_summary(guru_id: str, symbols: list[str] | None = None) -> Optional[Dict[str, Any]]:
    """
    아래 두 소스를 합쳐 최신 1건 반환:
    1) app/data/summaries/{guru}_summaries.jsonl
    2) app/data/summaries/market.jsonl  (키움 인제션)
    symbols가 있으면 해당 심볼 포함 레코드를 우선 선택.
    날짜 우선순위: updated > period_end > (content/text 내 YYYY-MM-DD)
    """
    path_guru = SUMMARIES_DIR / f"{guru_id.lower()}_summaries.jsonl"
    path_mkt  = SUMMARIES_DIR / "market.jsonl"

    rows = _read_jsonl(path_guru) + _read_jsonl(path_mkt)
    if not rows:
        return None

    if symbols:
        sset = set(symbols)
        pref = [r for r in rows if sset.intersection(r.get("symbols") or [])]
        rows = pref if pref else rows

    def score(rec: Dict[str, Any]) -> date:
        dt = _to_date(rec.get("updated"))
        if dt: return dt
        dt = _to_date(rec.get("period_end"))
        if dt: return dt
        dt = _extract_date_from_text(rec.get("content") or rec.get("text") or "")
        return dt or date.min

    rows.sort(key=score, reverse=True)
    return rows[0]

def load_profile_summary(guru_id: str) -> Optional[Dict[str, Any]]:
    """
    포트폴리오/철학(프로필성) 요약을 최신으로 1개 반환.
    - PRIORITY_SECTIONS 우선
    - 없으면 guru summaries의 최신 1개
    """
    path_guru = SUMMARIES_DIR / f"{guru_id.lower()}_summaries.jsonl"
    rows = _read_jsonl(path_guru)
    if not rows:
        return None

    def score_tuple(rec: Dict[str, Any]):
        sec = str(rec.get("section", "")).lower()
        prio = 0 if sec in PRIORITY_SECTIONS else 1
        dt = _to_date(rec.get("updated")) or _to_date(rec.get("period_end")) or _extract_date_from_text(rec.get("content") or rec.get("text") or "")
        return (prio, dt or date.min)

    rows.sort(key=score_tuple, reverse=True)  # 날짜 내림차순, 하지만 prio=0이 뒤로 밀릴 수 있음
    pri = [r for r in rows if str(r.get("section","")).lower() in PRIORITY_SECTIONS]
    return (pri or rows)[0]
