# app/services/symbol_resolver.py
import re
from functools import lru_cache

CODE_RE = re.compile(r"\b\d{6}\b")

def _norm(s: str) -> str:
    # 공백/특수문자 제거, 소문자
    return re.sub(r"[\s\W_]+", "", s or "").lower()

@lru_cache(maxsize=1)
def _build_index() -> dict:
    """
    KOSPI/KOSDAQ 전체 종목 인덱스(이름->코드) 1회 로드 + 캐시.
    pykrx 네트워크 호출을 최소화하기 위해 LRU 캐시 사용.
    """
    idx = {}
    try:
        from pykrx import stock
        for market in ["KOSPI", "KOSDAQ"]:
            for code in stock.get_market_ticker_list(market=market):
                name = stock.get_market_ticker_name(code) or ""
                idx[_norm(name)] = code
    except Exception:
        # pykrx가 실패하면 빈 인덱스(후술할 fallback에서 market.jsonl 기반 탐색 가능)
        pass

    # 자주 쓰는 별칭/약칭 몇 개만 예의상 추가 (원하면 확장)
    alias = {
        "삼전": "삼성전자",
        "하닉": "에스케이하이닉스",
        "하이닉스": "에스케이하이닉스",
        "현대차": "현대자동차",
        "기아차": "기아",
        "엘지전자": "LG전자",
        "엘지화학": "LG화학",
    }
    for a, canon in alias.items():
        if _norm(canon) in idx:
            idx[_norm(a)] = idx[_norm(canon)]
    return idx

def resolve_symbols_from_text(text: str) -> list[str]:
    """
    1) 질문에 '숫자 6자리'가 있으면 그대로 반환
    2) 없으면 '이름→코드' 인덱스로 탐색(부분일치 우선)
    3) 그래도 못 찾으면 [] 반환
    """
    if not text:
        return []
    # 1) 숫자코드 우선
    found = CODE_RE.findall(text)
    if found:
        return found

    idx = _build_index()
    key = _norm(text)
    hits = set()

    # (정확 일치)
    if key in idx:
        return [idx[key]]

    # (부분 일치: 가장 긴 이름 우선)
    for name_norm, code in idx.items():
        if name_norm and name_norm in key:
            hits.add(code)

    # 길이 제한
    return list(hits)[:3]

def known_codes_from_market_jsonl() -> dict:
    """
    market.jsonl에 등장한 코드들을 역으로 인덱싱(코드->True)
    pykrx 실패 시 질문에 코드가 없으면, 이 집합으로라도 필터링 가능.
    """
    from pathlib import Path
    import json
    base = Path(__file__).resolve().parents[2] / "app" / "data" / "summaries" / "market.jsonl"
    if not base.exists():
        return {}
    codes = {}
    for ln in base.read_text(encoding="utf-8", errors="ignore").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            rec = json.loads(ln)
            for c in rec.get("symbols") or []:
                if CODE_RE.fullmatch(str(c)):
                    codes[str(c)] = True
        except Exception:
            pass
    return codes
