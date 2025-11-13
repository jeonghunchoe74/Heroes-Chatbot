# app/services/rag_loader.py
# -*- coding: utf-8 -*-
"""
RAG 로더 (아주 단순/기본 스타일)

하는 일:
1) JSONL 파일을 안전하게 읽어서 파이썬 리스트로 변환
2) 퍼소나(규칙/톤/템플릿) 불러오기
3) intent + audience(신규/기존)에 맞게 간단 선별
4) 요약(JSONL)에서 "가장 최신" 1개 선택
"""

import json
import re
from datetime import date
from pathlib import Path
from typing import List, Dict, Any, Optional

# ------------------------------------------
# 0) 경로 (절대경로로 고정)
# ------------------------------------------
# __file__ = app/services/rag_loader.py
# parents[2] = 프로젝트 루트(app/.. 의 부모)
BASE_DIR = Path(__file__).resolve().parents[2]
PROMPTS_DIR = BASE_DIR / "app" / "data" / "prompts"      # 예: app/data/prompts/buffett.jsonl
SUMMARIES_DIR = BASE_DIR / "app" / "data" / "summaries"   # 예: app/data/summaries/buffett_summaries.jsonl

# YYYY-MM-DD 모양 찾는 간단한 정규식
DATE_RX = re.compile(r"\b(20\d{2})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b")

# ------------------------------------------
# 1) JSONL 안전 로더
# ------------------------------------------
def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    """
    JSONL을 안전하게 읽음.
    - 파일 없으면 []
    - BOM/빈 줄/깨진 줄은 건너뜀(에러로 죽지 않음)
    """
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
            # 어디가 깨졌는지 보기 좋게 한 줄 경고
            preview = (line[:80] + "...") if len(line) > 80 else line
            print(f"[WARN] JSONL parse skip {path.name}:{idx} -> {e} | {preview}")
            continue

    if not rows:
        print(f"[WARN] JSONL empty after parsing: {path}")
    return rows

# ------------------------------------------
# 2) 퍼소나(규칙/톤/템플릿) 로드
# ------------------------------------------
def load_persona_chunks(guru_id: str) -> List[Dict[str, Any]]:
    path = PROMPTS_DIR / f"{guru_id.lower()}.jsonl"
    return _read_jsonl(path)

def pick_persona_for_intent(chunks: List[Dict[str, Any]], intent: str, audience: str = "") -> List[Dict[str, Any]]:
    """
    intent + audience로 고르기.
    규칙:
    1) intent가 들어있는 청크만 먼저 고른다.
    2) audience가 비어있지 않으면, audience가 같은 것만 우선 사용한다.
        (단, audience가 비어있는 공통 청크는 항상 허용)
    3) 보조로 principles_core, tone_guide 섹션도 넣는다.
    4) 섹션별 1개만 남긴다.
    """
    i = (intent or "").lower()
    a = (audience or "").lower().strip()

    # 1) intent가 맞는 애들
    main: List[Dict[str, Any]] = []
    for c in chunks:
        intents = [str(x).lower() for x in c.get("intent", [])]
        if i in intents:
            main.append(c)

    # 2) audience 필터(간단)
    def aud_ok(c: Dict[str, Any]) -> bool:
        aud = str(c.get("audience", "")).lower().strip()
        if not a:   # auto이면 모두 허용
            return True
        if not aud: # 공통이면 모두 허용
            return True
        return aud == a

    main = [c for c in main if aud_ok(c)]

    # 3) 보조 섹션(원칙/톤)
    helpers: List[Dict[str, Any]] = []
    for c in chunks:
        sec = str(c.get("section", "")).lower()
        if sec in ["principles_core", "tone_guide"] and aud_ok(c):
            helpers.append(c)

    # 4) 섹션별 1개만
    picked: List[Dict[str, Any]] = []
    seen = set()
    for c in main + helpers:
        sec = c.get("section", "misc")
        if sec in seen:
            continue
        seen.add(sec)
        picked.append(c)

    return picked

# ------------------------------------------
# 3) 최신 요약 1개 로드
# ------------------------------------------
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

def load_latest_summary(guru_id: str) -> Optional[Dict[str, Any]]:
    """
    app/data/summaries/<guru>_summaries.jsonl 에서 최신 1개를 고른다.
    날짜 우선순위: updated > period_end > content 안의 YYYY-MM-DD
    """
    path = SUMMARIES_DIR / f"{guru_id.lower()}_summaries.jsonl"
    rows = _read_jsonl(path)
    if not rows:
        return None

    def score(rec: Dict[str, Any]) -> date:
        dt = _to_date(rec.get("updated"))
        if dt: return dt
        dt = _to_date(rec.get("period_end"))
        if dt: return dt
        dt = _extract_date_from_text(rec.get("content", ""))
        return dt or date.min

    rows.sort(key=score, reverse=True)
    return rows[0]
