from openai import OpenAI
from app.core.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

async def ask_gpt(messages):
    """GPT 호출 헬퍼"""
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
    )
    return res.choices[0].message.content

