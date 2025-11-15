import pandas as pd
from pathlib import Path

# 데이터 폴더 경로 지정
DATA_DIR = Path(__file__).parent.parent / "data"

def load_portfolio(guru_id: str) -> pd.DataFrame:
    """
    각 투자 대가(guru_id)에 해당하는 13F 또는 포트폴리오 엑셀 파일을 불러옵니다.
    파일이 없거나 읽기 실패 시, 빈 DataFrame을 반환합니다.
    """
    file_map = {
        "ark": DATA_DIR / "ARK_13F_25.xlsx",
        "wood": DATA_DIR / "ARK_13F_25.xlsx",
        "buffett": DATA_DIR / "Berkshire_13F_25.xlsx",
        "lynch": DATA_DIR / "peter_lynch_top10.xlsx",
        "peter": DATA_DIR / "peter_lynch_top10.xlsx",
    }

    file_path = file_map.get(guru_id.lower())

    # 파일 존재 여부 확인
    if not file_path or not file_path.exists():
        print(f"[WARN] Portfolio file not found for {guru_id}: {file_path}")
        return pd.DataFrame()

    # 엑셀 파일 읽기
    try:
        df = pd.read_excel(file_path)
        return df
    except Exception as e:
        print(f"[ERROR] Failed to read {file_path}: {e}")
        return pd.DataFrame()


def analyze_portfolio(df: pd.DataFrame) -> dict:
    """
    포트폴리오 데이터 요약:
      - 상위 섹터별 비중
      - 상위 보유 종목
      - 집중도 지표
    """
    if df is None or df.empty:
        return {}

    summary = {}
    if "sector" in df.columns and "weight(%)" in df.columns:
        # 섹터 비중 계산
        sector_weights = (
            df.groupby("sector")["weight(%)"].sum().sort_values(ascending=False)
        )
        summary["top_sectors"] = sector_weights.head(3).to_dict()

        # 상위 보유 종목 10개
        top_holdings = df.sort_values("weight(%)", ascending=False).head(10)
        summary["top_holdings"] = top_holdings[
            ["company", "ticker", "weight(%)"]
        ].to_dict(orient="records")

        # 상위 섹터 집중도 계산
        summary["concentration"] = round(sector_weights.head(3).sum(), 2)

    return summary


def format_portfolio_text(df: pd.DataFrame, max_rows: int = 10) -> str:
    """
    GPT 프롬프트용 텍스트 요약 생성.
    """
    if df is None or df.empty:
        return "No portfolio data available."

    try:
        text = df[["company", "ticker", "sector", "weight(%)"]].head(max_rows).to_string(index=False)
        return text
    except Exception:
        return "Portfolio data could not be formatted properly."
