import os
import uuid
import logging
from typing import TypedDict, Annotated, List, Dict, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# ✅ guru_service에서 프롬프트(엑셀 + 텍스트) 로드
from app.services.news_service import summarize_news
from app.services.guru_service import get_guru_prompt
from app.services.sector import get_top5, format_output, format_output_html


SECTOR_KEYWORDS = list({
    "반도체", "유틸리티", "금융서비스", "소프트웨어·서비스", "에너지", "소재",
    "자동차·부품", "통신서비스", "보험", "은행", "헬스케어 장비·서비스"
})

logger = logging.getLogger(__name__)

# 🔧 LLM 초기화
llm = ChatOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    model_name=os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o-mini")
)

# 📦 대화 상태 구조 정의
class State(TypedDict):
    messages: Annotated[List, add_messages]

# 🧩 LangGraph 구성
def chatbot(state: State):
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

workflow = StateGraph(State)
workflow.add_node("chatbot", chatbot)
workflow.add_edge(START, "chatbot")
workflow.add_edge("chatbot", END)
graph = workflow.compile()

# 💾 세션별 상태 저장
sessions: Dict[str, State] = {}

# 🧠 세션 생성 / 조회
def get_or_create_session(session_id: Optional[str] = None, guru_id: str = "buffett") -> tuple[str, State]:
    """세션 ID가 없으면 새 세션 생성 (guru_id 기반 프롬프트 포함)"""
    if session_id and session_id in sessions:
        logger.info(f"기존 세션 사용: {session_id}")
        return session_id, sessions[session_id]

    try:
        prompt_text = get_guru_prompt(guru_id)
        logger.info(f"{guru_id} 프롬프트 + 엑셀 로드 성공 ✅")
    except Exception as e:
        logger.warning(f"{guru_id} 프롬프트 로드 실패 ❌: {e}")
        prompt_text = (
            f"너는 {guru_id.title()}의 투자 철학을 가진 조언자다. "
            "데이터 로드에 실패했으므로 일반적인 가치투자 관점으로 답변해라."
        )

    new_session_id = str(uuid.uuid4())
    sessions[new_session_id] = {
        "messages": [SystemMessage(content=prompt_text)]
    }
    logger.info(f"새 세션 생성 완료: {new_session_id}")
    return new_session_id, sessions[new_session_id]

async def get_initial_message(guru_id: str):
    """
    챗봇 첫 로딩 시 — 대가 철학 + 뉴스 요약 반환
    """
    # ① 철학 요약 (buffett.txt의 앞부분 2~3문장 추출)
    full_prompt = get_guru_prompt(guru_id)
    # ✅ OpenAI로 '투자 철학 요약문' 생성
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    try:
        resp = client.responses.create(
            model="gpt-4o-mini",
            input=f"""
당신은 {guru_id}입니다.
다음 텍스트는 당신의 투자 철학입니다.
이를 바탕으로 당신의 투자 철학을 3~5문장으로 명확히, 따뜻한 말투로 소개해줘.
텍스트:
{full_prompt}
            """,
            temperature=0.6,
        )
        intro_text = resp.output_text.strip()
    except Exception as e:
        intro_text = "나는 오랜 경험을 통해 배운 투자 원칙을 따르는 사람입니다. 복잡함 대신 단순함을, 단기 이익보다 꾸준함을 믿습니다."
        print("[WARN] 투자 철학 요약 실패:", e)

    # ② 뉴스 요약
    news_items = summarize_news(guru_id)

    # ③ 구성
    return {
        "intro": intro_text,
        "news": news_items
    }

# 💬 GPT 응답 생성
async def generate_response(user_input: str, session_id: Optional[str] = None, guru_id: str = "buffett"):
    session_id, state = get_or_create_session(session_id, guru_id)
    state["messages"].append(HumanMessage(content=user_input))

    result = graph.invoke({"messages": state["messages"]})
    ai_response = result["messages"][-1].content

    # ✅ 섹터 자동 탐지 및 종목 리스트 추가
    for sector_name in SECTOR_KEYWORDS:
        if sector_name in ai_response:
            try:
                sector_info = format_output_html(sector_name)
                ai_response += f"\n\n{sector_info}"
                break
            except Exception as e:
                print("[WARN] sector info 추가 실패:", e)
                continue

    # 세션 상태 업데이트
    state["messages"] = result["messages"]
    sessions[session_id] = state
    logger.info(f"[{guru_id}] 세션 {session_id} 업데이트 완료 ({len(state['messages'])} messages)")

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
