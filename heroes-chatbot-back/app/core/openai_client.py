from openai import OpenAI
from app.core.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

async def ask_gpt(messages):
    """GPT 호출 헬퍼"""
    res = client.chat.completions.create(
        model="ft:gpt-4.1-mini-2025-04-14:personal:lynch:CbenYptC",
        messages=messages,
    )
    return res.choices[0].message.content

