# sector.py
from typing import List
import datetime as dt
import logging

try:
    from pykrx import stock as krx
    _PYKRX = True
except Exception:
    _PYKRX = False

logger = logging.getLogger(__name__)

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
    """인덱스 티커로 시총 상위 5개 기업을 가져옵니다."""
    if not _PYKRX:
        logger.warning("pyKRX is not available")
        return []
    if not index_ticker:
        logger.warning("Index ticker is empty")
        return []
    
    try:
        logger.debug("Fetching portfolio for index ticker: %s", index_ticker)
        members = list(krx.get_index_portfolio_deposit_file(index_ticker))
        if not members:
            logger.warning("No members found for index ticker: %s", index_ticker)
            return []
        logger.debug("Found %d members in index", len(members))
        
        today = _today_ymd()
        logger.debug("Fetching market cap for date: %s", today)
        df = krx.get_market_cap_by_ticker(today)
        
        if df is None or df.empty:
            logger.warning("Market cap data is empty for date: %s", today)
            return []
        
        if hasattr(df, "columns") and "티커" in df.columns:
            try:
                df = df.set_index("티커")
            except Exception:
                pass
        sidx = set(getattr(df, "index", []))
        inter = [t for t in members if t in sidx]
        logger.debug("Found %d overlapping tickers", len(inter))

        def mcap(t: str) -> int:
            try:
                row = df.loc[t]
                if "시가총액" in df.columns:
                    return int(row["시가총액"])
                return int(row[0])
            except Exception as e:
                logger.debug("Error getting market cap for ticker %s: %s", t, e)
                return 0

        top = sorted(inter, key=mcap, reverse=True)[:5]
        names: List[str] = []
        seen = set()
        for t in top:
            try:
                name = krx.get_market_ticker_name(t)
            except Exception as e:
                logger.debug("Error getting name for ticker %s: %s", t, e)
                name = t
            # ✅ 중복 이름 제거
            if name not in seen:
                names.append(name)
                seen.add(name)
        logger.info("Top 5 companies: %s", names)
        return names
    except Exception as e:
        logger.error("Error getting top 5 by index %s: %s", index_ticker, e, exc_info=True)
        return []

def get_top5(label_ko: str) -> List[str]:
    """섹터 라벨로 시총 상위 5개 기업을 가져옵니다."""
    label = ALIAS.get(label_ko, label_ko)  # 별칭 보정
    logger.info("Getting top 5 companies for sector: %s (mapped to: %s)", label_ko, label)
    tkr = LABEL_TO_INDEX.get(label)
    if not tkr:
        logger.warning("No index ticker found for sector: %s (mapped label: %s)", label_ko, label)
        return []
    companies = _top5_by_index(tkr)
    logger.info("Found %d companies for sector %s: %s", len(companies), label_ko, companies)
    return companies

def format_output(label_ko: str) -> str:
    names = get_top5(label_ko)
    return f"섹터 : {label_ko}\n종목명 리스트(시총 상위5개) : {', '.join(names)}"

# app/services/sector.py 안에 추가
def format_output_html(label_ko: str) -> str:
    """HTML 기반으로 보기 좋게 섹터/종목 리스트를 렌더링"""
    logger.info("Formatting HTML output for sector: %s", label_ko)
    names = get_top5(label_ko)
    if not names:
        logger.warning("No companies found for sector: %s", label_ko)
        return ""
    name_list = ", ".join(names)
    html_output = f"""<div style="margin-top: 12px; padding: 8px 12px; background: #F4F7FF; border-radius: 8px; font-size: 14px; line-height: 1.6;">
<p style="margin:0;"><strong>📊 섹터 :</strong> {label_ko}</p>
<p style="margin:4px 0 0 0;"><strong>종목명 Top5 :</strong> {name_list}</p>
</div>"""
    logger.info("Generated HTML output for sector %s with %d companies", label_ko, len(names))
    return html_output
