# app/mentors/registry.py
"""
멘토 에이전트 레지스트리
"""

from __future__ import annotations

import logging
from typing import Dict, Protocol

from app.mentors.types import MentorId

logger = logging.getLogger(__name__)


class MentorAgent(Protocol):
    """멘토 에이전트 인터페이스"""
    
    async def generate_response(
        self,
        query: str,
        intent: str,
        symbols: list[str],
        stock_metrics: list | None = None,
        macro_data: list | None = None,
        philosophy_snippets: list | None = None,
        portfolio_history: list | None = None,
    ) -> str:
        """응답 생성"""
        ...


# 멘토 에이전트 인스턴스 캐시
_agent_cache: Dict[MentorId, MentorAgent] = {}


def get_mentor_agent(guru_id: MentorId) -> MentorAgent:
    """
    멘토 에이전트 인스턴스 반환 (싱글톤).
    
    Args:
        guru_id: "buffett", "lynch", "wood"
        
    Returns:
        MentorAgent 인스턴스
    """
    from app.utils.mentor_utils import normalize_mentor_id
    normalized_id = normalize_mentor_id(guru_id)
    
    if normalized_id not in _agent_cache:
        if normalized_id == "buffett":
            from app.mentors.buffett_agent import BuffettAgent
            _agent_cache[normalized_id] = BuffettAgent()
        elif normalized_id == "lynch":
            from app.mentors.lynch_agent import LynchAgent
            _agent_cache[normalized_id] = LynchAgent()
        elif normalized_id == "wood":
            from app.mentors.wood_agent import WoodAgent
            _agent_cache[normalized_id] = WoodAgent()
        else:
            logger.warning(f"Unknown guru_id: {guru_id}, using buffett")
            from app.mentors.buffett_agent import BuffettAgent
            _agent_cache[normalized_id] = BuffettAgent()
    
    return _agent_cache[normalized_id]

