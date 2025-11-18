from app.core.openai_client import ask_gpt
from app.services.guru_service import get_guru_prompt

def generate_insight(guru_id, text):
    """13F 기반 데이터 강제 참조형 분석"""
    prompt = get_guru_prompt(guru_id)
    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": (
                f"Analyze the following topic strictly from your portfolio perspective:\n\n"
                f"{text}\n\n"
                f"Steps:\n"
                f"1. Identify which of your holdings (from your portfolio above) are related to this topic.\n"
                f"2. Discuss how the news or event could affect those specific companies or sectors.\n"
                f"3. Mention the company names explicitly (e.g., Tesla, Palantir, Zoom, etc.) if they appear in your holdings.\n"
                f"4. If none of your holdings are directly related, explain why this topic is outside your portfolio focus.\n"
                f"5. Provide an investor-style conclusion about potential portfolio impact."
            ),
        },
    ]
    return ask_gpt(messages)
