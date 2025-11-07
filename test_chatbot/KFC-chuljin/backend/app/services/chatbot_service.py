# app/services/chatbot_service.py
import os
import uuid
import logging
from typing import TypedDict, Annotated, List, Dict, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# ✅ 추가
from app.services.guru_service import get_guru_prompt

logger = logging.getLogger(__name__)

# 🔧 LLM 초기화
llm = ChatOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    model_name=os.getenv("OPENAI_DEFAULT_MODEL", "gpt-3.5-turbo")
)

# 📦 대화 상태 구조 정의
class State(TypedDict):
    messages: Annotated[List, add_messages]

# 🔁 LangGraph 구성
def chatbot(state: State):
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

workflow = StateGraph(State)
workflow.add_node("chatbot", chatbot)
workflow.add_edge(START, "chatbot")
workflow.add_edge("chatbot", END)
graph = workflow.compile()

# 💾 세션별 상태 저장소
sessions: Dict[str, State] = {}

# 🧠 세션 생성 / 조회
def get_or_create_session(session_id: Optional[str] = None) -> tuple[str, State]:
    if session_id and session_id in sessions:
        logger.info(f"기존 세션 사용: {session_id}")
        return session_id, sessions[session_id]

    # ✅ guru_service에서 프롬프트 로드 (buffet.txt 읽음)
    try:
        prompt_text = get_guru_prompt("buffet")  # ← app/data/prompts/buffet.txt 로드
        logger.info("Buffet 프롬프트 로드 완료.")
    except Exception as e:
        logger.warning(f"Buffet 프롬프트 로드 실패, 기본 문구 사용: {e}")
        prompt_text = (
            "너는 워렌 버핏이다(교육용). 말투는 쉽고 편하게, 한 단락 2~3문장. "
            "티커·가격·숫자 나열·전문용어·매수/매도 지시·이모지 금지. "
            "섹터 이름만 말해라(예: 금융, 부동산, 산업 자동화 등). "
            "핵심은 쉬운 사업, 꾸준한 이익, 바꾸기 어려운 강점, 믿을 만한 운영. "
            "가격이 비싸면 기다리고 적당하면 오래 들고 간다."
        )

    new_session_id = str(uuid.uuid4())
    sessions[new_session_id] = {
        "messages": [SystemMessage(content=prompt_text)]
    }
    logger.info(f"새 세션 생성: {new_session_id}")
    return new_session_id, sessions[new_session_id]

# 💬 GPT 응답 생성
async def generate_response(user_input: str, session_id: Optional[str] = None):
    session_id, state = get_or_create_session(session_id)
    state["messages"].append(HumanMessage(content=user_input))
    result = graph.invoke({"messages": state["messages"]})
    ai_response = result["messages"][-1].content
    state["messages"] = result["messages"]
    sessions[session_id] = state
    logger.info(f"세션 {session_id} 업데이트 완료 (총 {len(state['messages'])}개 메시지)")
    return ai_response, session_id

# 🔄 세션 초기화
def reset_session(session_id: Optional[str] = None):
    if session_id and session_id in sessions:
        del sessions[session_id]
        return f"세션 {session_id}이 초기화되었습니다."
    else:
        count = len(sessions)
        sessions.clear()
        return f"모든 세션({count}개)이 초기화되었습니다."
