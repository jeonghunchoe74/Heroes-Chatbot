# sector.py
from typing import List
import datetime as dt

try:
    from pykrx import stock as krx
    _PYKRX = True
except Exception:
    _PYKRX = False

LABEL_TO_INDEX = {
    "에너지": "1154",
    "소재": "1153",
    "자본재": "1159",
    "상업·전문 서비스": "1026",
    "운송": "1019",
    "자동차·부품": "1015",
    "내구소비재·의류": "1006",
    "소비자 서비스": "1026",
    "임의소비재 유통·소매": "1016",
    "필수소비재 유통·소매": "1157",
    "식품·음료·담배": "1005",
    "생활용품": "1157",
    "헬스케어 장비·서비스": "1160",
    "제약·바이오·생명과학": "1009",
    "은행": "1022",
    "금융서비스": "1021",
    "보험": "1025",
    "소프트웨어·서비스": "1155",
    "기술하드웨어·장비": "1013",
    "반도체·장비": "1013",
    "통신서비스": "1150",
    "미디어·엔터테인먼트": "1026",
    "유틸리티": "1017",
    "주식형 REITs": None,
    "부동산 관리·개발": None,
}

# (요약 모듈이 '반도체' 처럼 다르게 줄 수도 있으니, 최소한의 별칭 보정)
ALIAS = {
    "반도체": "반도체·장비",
}

def _today_ymd() -> str:
    return dt.date.today().strftime("%Y%m%d")

def _top5_by_index(index_ticker: str) -> List[str]:
    if not _PYKRX or not index_ticker:
        return []
    try:
        members = list(krx.get_index_portfolio_deposit_file(index_ticker))
        if not members:
            return []
        df = krx.get_market_cap_by_ticker(_today_ymd())
        if hasattr(df, "columns") and "티커" in df.columns:
            try:
                df = df.set_index("티커")
            except Exception:
                pass
        sidx = set(getattr(df, "index", []))
        inter = [t for t in members if t in sidx]

        def mcap(t: str) -> int:
            try:
                row = df.loc[t]
                if "시가총액" in df.columns:
                    return int(row["시가총액"])
                return int(row[0])
            except Exception:
                return 0

        top = sorted(inter, key=mcap, reverse=True)[:5]
        names: List[str] = []
        seen = set()
        for t in top:
            try:
                name = krx.get_market_ticker_name(t)
            except Exception:
                name = t
            # ✅ 중복 이름 제거
            if name not in seen:
                names.append(name)
                seen.add(name)
        return names
    except Exception:
        return []

def get_top5(label_ko: str) -> List[str]:
    label = ALIAS.get(label_ko, label_ko)  # 별칭 보정
    tkr = LABEL_TO_INDEX.get(label)
    if not tkr:
        return []
    return _top5_by_index(tkr)

def format_output(label_ko: str) -> str:
    names = get_top5(label_ko)
    return f"섹터 : {label_ko}\n종목명 리스트(시총 상위5개) : {', '.join(names)}"

# app/services/sector.py 안에 추가
def format_output_html(label_ko: str) -> str:
    """HTML 기반으로 보기 좋게 섹터/종목 리스트를 렌더링"""
    names = get_top5(label_ko)
    if not names:
        return ""
    name_list = ", ".join(names)
    return f"""
    <div style="margin-top: 12px; padding: 8px 12px; background: #F4F7FF; border-radius: 8px; font-size: 14px; line-height: 1.6;">
      <p style="margin:0;"><strong>📊 섹터 :</strong> {label_ko}</p>
      <p style="margin:4px 0 0 0;"><strong>종목명 Top5 :</strong> {name_list}</p>
    </div>
    """
