print("🔥 guru_service loaded", flush=True)


# app/services/guru_service.py
import json
from pathlib import Path
from app.services.portfolio_service import (
    load_portfolio,
    analyze_portfolio,
    format_portfolio_text
)

PROMPTS_PATH = Path(__file__).parent.parent / "models" / "guru_prompts.json"

def load_prompts():
    with open(PROMPTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_guru_prompt(guru_id: str):
    print(f"🚀 get_guru_prompt 호출됨, guru_id={guru_id}", flush=True)
    """
    특정 guru의 엑셀 데이터 + 텍스트 프롬프트를 병합해 GPT system prompt 생성
    """

    # 1️⃣ 13F 엑셀 데이터 로드
    df = load_portfolio(guru_id)
    portfolio_text = (
        df.head(10).to_string(index=False)
        if not df.empty
        else "No portfolio data available."
    )

    # 2️⃣ 추가 프롬프트 텍스트 로드 (예: app/data/prompts/buffett.txt)
    base_path = Path("app/data/prompts")
    txt_path = base_path / f"{guru_id.lower()}.txt"

    extra_prompt = ""
    if txt_path.exists():
        try:
            extra_prompt = txt_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"[WARN] Could not read {txt_path}: {e}")
    else:
        print(f"[INFO] No custom prompt found for {guru_id}")

    # 3️⃣ GPT에게 전달할 통합 프롬프트 생성
    merged_prompt = f"""
You are acting as **{guru_id.title()}**, an investor with a unique philosophy.

Below is your latest 13F portfolio snapshot:
{portfolio_text}

Additionally, here is your personal investment philosophy and tone guidance:
{extra_prompt}

When analyzing market news or stock events:
- Use your real portfolio data for context.
- Respond in your characteristic style and reasoning.
- Discuss how the event aligns (or conflicts) with your investment philosophy.
- 시황에 대해서 최신 데이터를 최대한 정확하게 가져와서 근거로 사용하기
- 한글로 말하기
"""

    return merged_prompt
