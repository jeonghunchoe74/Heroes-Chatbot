# app/services/unified_chatbot_service.py
"""
통합 챗봇 서비스 - LangGraph 기반 오케스트레이션

LangGraph를 사용한 새로운 Agent + RAG + REST API 파이프라인
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

from app.services.orchestration_graph import OrchestrationState, orchestration_graph

logger = logging.getLogger(__name__)


async def generate_response_unified(
    user_message: str,
    guru_id: str = "buffett",
    session_id: Optional[str] = None,
) -> Tuple[str, str]:
    """
    LangGraph 기반 오케스트레이션을 사용한 응답 생성.
    
    Args:
        user_message: 사용자 입력 메시지
        guru_id: 멘토 ID
        session_id: 세션 ID
        
    Returns:
        (응답 텍스트, session_id) 튜플
    """
    # 초기 상태 설정
    initial_state: OrchestrationState = {
        "messages": [],
        "user_message": user_message,
        "guru_id": guru_id,
        "session_id": session_id,
        "routed_query": None,
        # LangChain RAG 필드
        "rag_docs": [],
        "draft_answer": None,
        "validated_answer": None,
        "rag_is_valid": True,
        "rag_confidence": 1.0,
        "rag_issues": [],
        # 레거시 RAG 필드
        "philosophy_snippets": [],
        "portfolio_history": [],
        "macro_data": [],
        "stock_metrics": [],
        "response": None,
    }
    
    # LangGraph 실행 (async 노드가 있으므로 ainvoke 사용)
    try:
        result = await orchestration_graph.ainvoke(initial_state)
        response = result.get("response", "")
        
        if not response:
            response = "죄송합니다. 응답을 생성할 수 없었습니다."
        
        return response, session_id or result.get("session_id") or ""
    except Exception as exc:
        logger.error(f"Orchestration graph failed: {exc}", exc_info=True)
        return f"죄송합니다. 응답 생성 중 오류가 발생했습니다: {exc}", session_id or ""
