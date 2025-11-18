from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


# 투자 성향 테스트 관련 스키마
class TestResultRequest(BaseModel):
    scores: Dict[str, int] = Field(..., description="테스트 점수")
    answers: Dict[str, str] = Field(default_factory=dict, description="답변 내용")


class TestResultResponse(BaseModel):
    risk_profile: str = Field(..., description="리스크 프로필 (conservative, moderate, aggressive)")
    matched_guru_id: str = Field(..., description="매칭된 투자 대가 ID")
    matched_gurus: List[str] = Field(..., description="매칭된 투자 대가 목록")
    explanation: str = Field(..., description="매칭 설명")


# 뉴스 관련 스키마
class NewsItem(BaseModel):
    id: str
    title: str
    content: str
    source: str
    url: str
    published_at: str
    category: str = "general"


class NewsResponse(BaseModel):
    news: List[NewsItem]


# 인사이트 관련 스키마
class InsightRequest(BaseModel):
    news_id: str = Field(..., description="뉴스 ID")
    guru_id: Optional[str] = Field(None, description="투자 대가 ID")


class InsightResponse(BaseModel):
    news_id: str
    guru_id: Optional[str]
    insight: str
    news_title: str


# 채팅 관련 스키마
class ChatMessage(BaseModel):
    room_id: str = Field(..., description="채팅방 ID")
    guru_id: str = Field(..., description="투자 대가 ID")
    content: str = Field(..., description="메시지 내용")
    user_id: Optional[str] = Field(None, description="사용자 ID")


class ChatResponse(BaseModel):
    room_id: str
    guru_response: str
    status: str

