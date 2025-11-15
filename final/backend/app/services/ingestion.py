import os, json
from datetime import datetime
from typing import Dict, Any, List
from .kiwoom_client import KiwoomClient

DATA_DIR = "app/data"
RAW_DIR = os.path.join(DATA_DIR, "summaries", "raw")
SUMM_PATH = os.path.join(DATA_DIR, "summaries", "market.jsonl")

# 콤마 구분 환경변수 지원 (예: "005930,000660,035420")
CODES = os.getenv("KIWOOM_CODES", "005930,000660,035420").split(",")

def _to_float(x):
    try: return float(str(x).replace(",", ""))
    except Exception: return None

def _to_ymd(s: str | None) -> str | None:
    if not s: return None
    s = str(s).strip().replace(".", "").replace("-", "")
    try:
        if len(s) == 8:
            dt = datetime.strptime(s, "%Y%m%d")
        else:
            dt = datetime.strptime(s[:10], "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return None

def _norm_ka10001(item: Dict[str, Any], fallback_date: str) -> Dict[str, Any]:
    """
    ka10001 응답을 RAG JSONL 스키마로 정규화
    네가 준 키에 정확히 맞춤:
      cur_prc, open_pric, high_pric, low_pric, flu_rt, trde_qty,
      oyr_hgst, oyr_lwst, per, eps, pbr, bps, mac, flo_stk
    + dvd_yld(있으면), trd_dd/date(있으면)
    + 거래대금 = 현재가 * 거래량 (TRADE_VALUE)
    """
    code    = item.get("stk_cd") or item.get("_stk_cd") or item.get("code")
    updated = _to_ymd(item.get("trd_dd")) or _to_ymd(item.get("date")) or fallback_date

    cur = _to_float(item.get("cur_prc"))
    vol = _to_float(item.get("trde_qty"))
    trade_value = (cur * vol) if (cur is not None and vol is not None) else None

    # 배당수익률: ka10001에 없을 수 있음(없으면 None)
    div_yield = _to_float(item.get("dvd_yld") or item.get("div_yield"))

    rec = {
        "section": "market_update",
        "intent": ["news_analysis"],
        "audience": [""],
        "updated": updated,
        "symbols": [code] if code else [],
        "metadata": {
            "source": "kiwoom/rest",
            "api_id": "ka10001",
            "metrics": {
                # 버핏 세트
                "PER": _to_float(item.get("per")),
                "PBR": _to_float(item.get("pbr")),
                "BPS": _to_float(item.get("bps")),
                "EPS": _to_float(item.get("eps")),
                "DIV_YIELD": div_yield,
                "MKT_CAP": _to_float(item.get("mac")),
                # 린치/우드 공통
                "52W_H": _to_float(item.get("oyr_hgst")),
                "52W_L": _to_float(item.get("oyr_lwst")),
                "CHG_RT": _to_float(item.get("flu_rt")),
                "VOL": vol,
                "TRADE_VALUE": trade_value,
                # 참고값
                "CUR": cur,
            },
        },
    }

    per = rec["metadata"]["metrics"]["PER"]
    pbr = rec["metadata"]["metrics"]["PBR"]
    rec["text"] = f"{code} 스냅샷: PER {per} PBR {pbr}".strip()
    return rec

async def run_daily_ingestion():
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(SUMM_PATH), exist_ok=True)

    client = KiwoomClient()   # env: KIWOOM_BASE_URL, KIWOOM_ACCESS_TOKEN
    raw_list = await client.ka10001_batch(CODES)
    await client.close()

    # 원본 백업
    ymd_compact = datetime.now().strftime("%Y%m%d")
    with open(os.path.join(RAW_DIR, f"ka10001_{ymd_compact}.json"), "w", encoding="utf-8") as f:
        json.dump(raw_list, f, ensure_ascii=False, indent=2)

    # 정규화 → market.jsonl append
    today = datetime.now().strftime("%Y-%m-%d")
    records: List[Dict[str, Any]] = []
    for item in raw_list:
        if isinstance(item, dict) and (item.get("return_code") in (0, "0", None)) and not item.get("_error"):
            records.append(_norm_ka10001(item, fallback_date=today))

    with open(SUMM_PATH, "a", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"[INGEST] ka10001 normalized {len(records)} recs -> {SUMM_PATH}")
