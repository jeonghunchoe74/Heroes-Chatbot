# app/services/symbol_resolver.py
import re
from functools import lru_cache

CODE_RE = re.compile(r"\b\d{6}\b")

def _norm(s: str) -> str:
    # 공백/특수문자 제거, 소문자
    return re.sub(r"[\s\W_]+", "", s or "").lower()

# pykrx 미사용/실패 시에도 동작하도록 로컬 별칭(상용 빈도 높은 이름 -> 코드) 제공
# 필요에 따라 확장 가능
LOCAL_ALIASES: dict[str, str] = {
    # 자주 쓰는 로컬 별칭(이름 -> 코드)
    "키움증권": "039490",
    # 대형주 예시 (상황 맞춰 확장)
    "삼성전자": "005930",
    "SK하이닉스": "000660",
    "현대자동차": "005380",
    "기아": "000270",
    "LG전자": "066570",
    "LG화학": "051910",
    "카카오": "035720",
}

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
    2) 없으면 로컬 별칭(LOCAL_ALIASES)으로 우선 탐색
    3) 그래도 없으면 '이름→코드' 인덱스로 탐색(부분일치 우선)
    4) 그래도 못 찾으면 [] 반환
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if not text:
        return []
    # 1) 숫자코드 우선
    found = CODE_RE.findall(text)
    if found:
        logger.debug(f"[SYMBOL_RESOLVER] Found code in text: {found}")
        return found

    # 2) 로컬 별칭 우선 매칭 (pykrx 미설치/실패 환경 대비)
    key = _norm(text)
    token_text = re.sub(r"[^0-9a-z가-힣]+", " ", (text or "").lower())
    token_set = set(filter(None, token_text.split()))
    local_hits = []
    for name, code in LOCAL_ALIASES.items():
        try:
            norm_name = _norm(name)
            if norm_name in key:
                logger.debug(f"[SYMBOL_RESOLVER] Found local alias match: '{name}' -> '{code}' in text '{text[:50]}'")
                local_hits.append(code)
        except Exception as exc:
            logger.debug(f"[SYMBOL_RESOLVER] Error matching alias '{name}': {exc}")
            continue
    if local_hits:
        # 중복 제거 후 상위 3개
        result = list(dict.fromkeys(local_hits))[:3]
        logger.info(f"[SYMBOL_RESOLVER] Resolved symbols from local aliases: {result}")
        return result

    idx = _build_index()
    hits = set()

    # (정확 일치)
    if key in idx:
        result = [idx[key]]
        logger.info(f"[SYMBOL_RESOLVER] Found exact match in index: {result}")
        return result

    # (부분 일치: 가장 긴 이름 우선)
    for name_norm, code in idx.items():
        if not name_norm:
            continue
        if len(name_norm) < 3:
            # 짧은 이름(EG 등)은 토큰 단위로만 비교해 PEG 같은 용어와 충돌하지 않도록 처리
            if name_norm in token_set:
                hits.add(code)
                logger.debug(f"[SYMBOL_RESOLVER] Token match (short name): '{name_norm}' -> '{code}'")
            continue
        if name_norm in key:
            hits.add(code)
            logger.debug(f"[SYMBOL_RESOLVER] Found partial match: '{name_norm}' -> '{code}'")

    # 길이 제한
    result = list(hits)[:3]
    if result:
        logger.info(f"[SYMBOL_RESOLVER] Resolved symbols from index: {result}")
    else:
        logger.warning(f"[SYMBOL_RESOLVER] Could not resolve symbols from text: '{text[:100]}'")
    return result

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
