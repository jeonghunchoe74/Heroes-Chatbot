# app/services/chatbot_service.py
# ===============================
# 챗봇의 "뇌" 역할을 하는 서비스:
# - 세션(대화방) 만들기/찾기
# - 챗봇에게 말 시키기
# - 초기 화면용 intro/news 만들기

import os
import uuid
import logging
from typing import List, Dict, Optional, Tuple, TypedDict, Annotated

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# 프로젝트 내부 서비스(있다고 가정)
from app.services.news_service import summarize_news
from app.services.guru_service import get_guru_prompt
from app.services.sector import format_output_html

logger = logging.getLogger(__name__)

# 언어모델 준비(환경변수 사용)
llm = ChatOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    model_name=os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o-mini"),
)

# 대화 상태(메시지 리스트를 담는다)
class State(TypedDict):
    messages: Annotated[List, add_messages]

# "한 번 말하기" 단계
def _chatbot_step(state: State):
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

# LangGraph로 간단 파이프라인 구성
workflow = StateGraph(State)
workflow.add_node("chatbot", _chatbot_step)
workflow.add_edge(START, "chatbot")
workflow.add_edge("chatbot", END)
graph = workflow.compile()

# 메모리에 세션 저장(간단 버전)
sessions: Dict[str, State] = {}

def get_or_create_session(session_id: Optional[str] = None,
                        guru_id: str = "buffett") -> Tuple[str, State]:
    """
    세션ID가 있으면 그걸로, 없으면 새로 만들어 반환.
    """
    if session_id and session_id in sessions:
        logger.info(f"[session] 기존 세션 사용: {session_id}")
        return session_id, sessions[session_id]

    # 새 세션의 시작 메시지(시스템 프롬프트) 준비
    try:
        prompt_text = get_guru_prompt(guru_id)
        logger.info(f"[session] {guru_id} 프롬프트 로드 성공")
    except Exception as e:
        logger.warning(f"[session] {guru_id} 프롬프트 로드 실패: {e}")
        prompt_text = (
            f"너는 {guru_id.title()}의 투자 철학을 가진 조언자다. "
            "데이터 로드에 실패했으니, 일반적인 가치투자 관점으로 차분하게 답해라."
        )

    new_session_id = str(uuid.uuid4())
    sessions[new_session_id] = {"messages": [SystemMessage(content=prompt_text)]}
    logger.info(f"[session] 새 세션 생성: {new_session_id}")
    return new_session_id, sessions[new_session_id]

async def get_initial_message(guru_id: str) -> Dict[str, object]:
    """
    초기 화면용 데이터:
    - intro: 투자 철학 간단 소개(따뜻한 말투)
    - news: 최신 뉴스 요약 (반드시 list 보장)
    """
    # 1) 투자 철학 전체 텍스트
    full_prompt = get_guru_prompt(guru_id)

    # 2) 소개문 만들기(실패 시 기본문구)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        resp = client.responses.create(
            model="gpt-4o-mini",
            input=(
                f"당신은 {guru_id}입니다.\n"
                "다음 텍스트(투자 철학)를 3~5문장으로 쉽고 따뜻하게 소개해 주세요.\n\n"
                f"{full_prompt}\n"
            ),
            temperature=0.6,
        )
        intro_text = resp.output_text.strip()
    except Exception as e:
        logger.warning(f"[initial] 투자 철학 요약 실패: {e}")
        intro_text = (
            "나는 오랜 경험을 통해 배운 투자 원칙을 따르는 사람입니다. "
            "복잡함 대신 단순함을, 단기 이익보다 꾸준함을 믿습니다."
        )

    # 3) 뉴스 요약(반드시 list 보장)
    try:
        news_items = summarize_news(guru_id)
        if not isinstance(news_items, list):
            news_items = []
    except Exception as e:
        logger.warning(f"[initial] 뉴스 요약 실패: {e}")
        news_items = []

    return {"intro": intro_text, "news": news_items}

async def generate_response(user_input: str,
                            session_id: Optional[str] = None,
                            guru_id: str = "buffett",
                            user_type: str = "auto") -> Tuple[str, str]:
    """
    사용자의 말에 대한 챗봇의 답을 생성.
    """
    logger.info(f"[generate] guru={guru_id}, user_type={user_type}, in_sid={session_id}")

    # 세션 준비
    session_id, state = get_or_create_session(session_id, guru_id)

    # 사용자 메시지 추가
    state["messages"].append(HumanMessage(content=user_input))

    # 한 턴 실행
    result = graph.invoke({"messages": state["messages"]})
    ai_response: str = result["messages"][-1].content  # 마지막 메시지가 챗봇 발화

    # 섹터 키워드가 들어있으면 HTML 표를 덧붙여 주기(있다면만)
    SECTOR_KEYWORDS = [
        "반도체", "유틸리티", "금융서비스", "소프트웨어·서비스", "에너지", "소재",
        "자동차·부품", "통신서비스", "보험", "은행", "헬스케어 장비·서비스"
    ]
    try:
        for sector_name in SECTOR_KEYWORDS:
            if sector_name in ai_response:
                sector_html = format_output_html(sector_name)
                ai_response += f"\n\n{sector_html}"
                break
    except Exception as e:
        logger.warning(f"[generate] 섹터 HTML 추가 실패: {e}")

    # 대화 기록 저장(다음 턴 이어서 말하려고)
    state["messages"] = result["messages"]
    sessions[session_id] = state
    logger.info(f"[generate] 세션 갱신 완료 sid={session_id}, 총 메시지수={len(state['messages'])}")

    return ai_response, session_id

def reset_session(session_id: Optional[str] = None) -> str:
    """
    특정 세션만 지우거나, 전체 세션을 지운다.
    """
    if session_id and session_id in sessions:
        del sessions[session_id]
        return f"세션 {session_id}이 초기화되었습니다."
    else:
        count = len(sessions)
        sessions.clear()
        return f"모든 세션({count}개)이 초기화되었습니다."
