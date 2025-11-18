def build_guru_prompt(base_prompt: str, guru_id: str, summary: dict, holdings_text: str):
    """
    GPT가 실제 엑셀 데이터를 반드시 참고하도록 설계된 고정형 프롬프트
    """

    top_sectors = summary.get("top_sectors", {})
    concentration = summary.get("concentration", 0)

    prompt = f"{base_prompt}\n\n"
    prompt += f"You are {guru_id.capitalize()}, an investor whose analysis must be strictly based on your real 13F portfolio data.\n\n"

    # ✅ 실제 섹터 데이터 명시
    if top_sectors:
        sectors = ", ".join([f"{k} ({v:.1f}%)" for k, v in top_sectors.items()])
        prompt += f"Top sectors by weight: {sectors}.\n"

    # ✅ 집중도
    if concentration > 50:
        prompt += f"You maintain a concentrated portfolio (Top 3 sectors = {concentration}%).\n"
    else:
        prompt += f"You have a diversified portfolio (Top 3 sectors = {concentration}%).\n"

    # ✅ 포트폴리오 데이터 삽입
    prompt += "\nYour latest 13F top holdings:\n"
    prompt += f"{holdings_text}\n\n"

    # ✅ “반드시 참조해야 한다”는 명령문 추가
    prompt += (
        "When analyzing any news, market trend, or company:\n"
        "1. You MUST cross-check the companies and sectors mentioned with your 13F holdings above.\n"
        "2. If a company or sector overlaps with your portfolio, explicitly mention it by name.\n"
        "3. Explain how the news impacts your exposure or strategy regarding those holdings.\n"
        "4. Do not give a generic market summary — reason entirely from your portfolio’s composition.\n"
        "5. If the topic is unrelated to your holdings, state that clearly and explain why.\n"
        "When answering, explicitly refer to the companies listed above. \n"
        "If Tesla, Palantir, Roku, or other AI-related holdings appear, analyze their exposure. \n"
        "Always tie your reasoning back to your actual portfolio composition.\n"
    )

    return prompt
