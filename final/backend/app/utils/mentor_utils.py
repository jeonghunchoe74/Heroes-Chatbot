# app/utils/mentor_utils.py
"""
멘토 ID 정규화 유틸리티
"""

from __future__ import annotations

from typing import Literal

MentorId = Literal["buffett", "lynch", "wood"]


def normalize_mentor_id(guru_id: str) -> MentorId:
    """
    멘토 ID를 정규화합니다.
    
    Args:
        guru_id: 원본 멘토 ID (buffett, lynch, wood, ark, cathie, cathie_wood 등)
        
    Returns:
        정규화된 멘토 ID ("buffett", "lynch", "wood" 중 하나)
    """
    if not guru_id:
        return "buffett"
    
    normalized = guru_id.lower().strip()
    
    # wood 관련 정규화
    if normalized in ("ark", "cathie", "cathie_wood", "wood"):
        return "wood"
    
    # 기타 정규화
    if normalized in ("buffett", "warren", "warren_buffett"):
        return "buffett"
    
    if normalized in ("lynch", "peter", "peter_lynch"):
        return "lynch"
    
    # 기본값
    return "buffett"

