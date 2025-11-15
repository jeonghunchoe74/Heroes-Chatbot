# app/services/llm_service.py
"""
LLM 서비스 - OpenAI ChatCompletion 호출 전담

역할:
- 모든 LLM 호출을 이 모듈에서만 수행
- 모델 변경 시 이 모듈만 수정하면 되도록 설계
- 멘토별 모델 설정 지원
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from openai import OpenAI

logger = logging.getLogger(__name__)

# 모델 설정
DEFAULT_MODEL = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o-mini")
DEFAULT_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))

# 멘토별 모델 매핑 (환경변수로 오버라이드 가능)
MODEL_MAP = {
    "buffett": os.getenv("OPENAI_MODEL_BUFFETT", DEFAULT_MODEL),
    "lynch": os.getenv("OPENAI_MODEL_LYNCH", DEFAULT_MODEL),
    "wood": os.getenv("OPENAI_MODEL_WOOD", DEFAULT_MODEL),
}

# OpenAI 클라이언트 (직접 호출용)
_openai_client: Optional[OpenAI] = None


def _get_openai_client() -> OpenAI:
    """OpenAI 클라이언트 싱글톤"""
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def _get_chat_openai(model_kind: str = "mentor", guru_id: Optional[str] = None) -> ChatOpenAI:
    """
    ChatOpenAI 인스턴스 생성.
    
    Args:
        model_kind: "mentor" 또는 다른 종류
        guru_id: 멘토 ID (model_kind가 "mentor"일 때 사용)
        
    Returns:
        ChatOpenAI 인스턴스
    """
    if model_kind == "mentor" and guru_id:
        model_name = MODEL_MAP.get(guru_id, DEFAULT_MODEL)
    else:
        model_name = DEFAULT_MODEL
    
    return ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        model_name=model_name,
        temperature=DEFAULT_TEMPERATURE,
    )


async def invoke_llm(
    messages: List[Dict[str, str]],
    model_kind: str = "mentor",
    guru_id: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """
    LLM을 호출하여 응답을 반환.
    
    Args:
        messages: [{"role": "system", "content": "..."}, ...] 형식
        model_kind: "mentor" 또는 다른 종류
        guru_id: 멘토 ID (model_kind가 "mentor"일 때)
        temperature: 온도 설정 (None이면 기본값 사용)
        max_tokens: 최대 토큰 수
        
    Returns:
        LLM 응답 텍스트
    """
    if not messages:
        raise ValueError("messages가 비어있습니다.")
    
    # ChatOpenAI 사용
    llm = _get_chat_openai(model_kind=model_kind, guru_id=guru_id)
    
    # LangChain 메시지 형식으로 변환
    langchain_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        if role == "system":
            langchain_messages.append(SystemMessage(content=content))
        elif role == "assistant":
            langchain_messages.append(AIMessage(content=content))
        else:
            langchain_messages.append(HumanMessage(content=content))
    
    # 호출
    try:
        response = await llm.ainvoke(langchain_messages)
        return response.content
    except Exception as exc:
        logger.error(f"LLM 호출 실패: {exc}", exc_info=True)
        raise


async def invoke_llm_direct(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """
    OpenAI 클라이언트를 직접 사용하여 호출 (구조화된 응답 등 특수 케이스용).
    
    Args:
        messages: [{"role": "system", "content": "..."}, ...] 형식
        model: 모델명 (None이면 기본값)
        temperature: 온도 설정
        max_tokens: 최대 토큰 수
        
    Returns:
        LLM 응답 텍스트
    """
    client = _get_openai_client()
    
    completion = client.chat.completions.create(
        model=model or DEFAULT_MODEL,
        messages=messages,
        temperature=temperature or DEFAULT_TEMPERATURE,
        max_tokens=max_tokens,
    )
    
    return completion.choices[0].message.content


def get_model_for_guru(guru_id: str) -> str:
    """멘토별 모델명 반환"""
    return MODEL_MAP.get(guru_id, DEFAULT_MODEL)

