# 실행 방법:
# 1. 환경변수 설정: export OPENAI_API_KEY="your-api-key-here"
# 2. 패키지 설치: pip install fastapi uvicorn langgraph langchain-openai python-dotenv
# 3. 서버 실행: uvicorn main:app --reload

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import TypedDict, Annotated, List, Dict, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
import os
from dotenv import load_dotenv
import uuid
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(override=True)
api_key = os.getenv("OPENAI_API_KEY")
default_model = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-3.5-turbo")

# 환경 변수 검증
if not api_key:
    raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

# FastAPI 앱 설정
app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 요청/응답 모델
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str

# LangGraph State 정의
class State(TypedDict):
    messages: Annotated[List, add_messages]

llm = ChatOpenAI(api_key=api_key, model_name=default_model)

# 챗봇 노드
def chatbot(state: State):
    response = llm.invoke(state['messages'])
    return {"messages": [response]}

# LangGraph 그래프 생성
workflow = StateGraph(State)
workflow.add_node("chatbot", chatbot)
workflow.add_edge(START, "chatbot")
workflow.add_edge("chatbot", END)
graph = workflow.compile()

# 세션별 대화 상태 저장 (메모리)
sessions: Dict[str, State] = {}

def get_or_create_session(session_id: Optional[str] = None) -> tuple[str, State]:
    """세션 가져오기 또는 생성"""
    if session_id and session_id in sessions:
        logger.info(f"기존 세션 사용: {session_id}")
        return session_id, sessions[session_id]
    
    # 새 세션 생성
    new_session_id = str(uuid.uuid4())
    sessions[new_session_id] = {
        "messages": [SystemMessage(content="너는 워렌 버핏이다(교육용). 말투는 쉽고 편하게, 한 단락 2~3문장. 티커·가격·숫자 나열·전문용어·매수/매도 지시·이모지 금지. 포트폴리오/13F/파일/도구/“우리” 같은 자기 언급 금지. 섹터 이름만 말해라(예: 마트/필수소비재, 금융, 건설, 부동산·REITs, 물류·운송, 산업 자동화, 공공인프라·유틸리티, 테크하드웨어 등). [버핏식 판단(핵심)] 쉬운 사업인지 → 꾸준히 돈을 버는지 → 바꾸기 어려운 강점(브랜드·네트워크·전환비용)이 있는지 → 믿을 만한 운영인지 → 비싸면 기다리고 적당하면 오래 들고 간다. [버핏의 인격/태도(추가)] - 겸손과 절제: 모르면 모른다. 모호하면 한 가지 정보만 더 물어본다. - 인내와 규율: 좋은 회사라도 가격이 과하면 기다린다(행동하지 않을 자유). - 장기 파트너십: 경영진의 정직함·자본배분 태도를 중시한다. - 단순함 선호: 복잡한 이론 대신 평이한 비유와 일상 관찰을 쓴다. - 차분함: 공포/탐욕의 소음은 줄이고, 사실과 원칙만 말한다. - 책임감: 단정적 예언·타이밍 조언을 피하고, 스스로 생각하도록 돕는다. - 정정: 잘못 이해했음을 깨달으면 다음 문장에서 짧게 바로잡는다. [의도 감지 → 출력 형식] 1) 철학 질문(예: “너의 주식 철학은?”): - 버핏 철학만 2~3문장으로 간단히; 섹터 나열 금지. - 템플릿: “핵심은 내가 이해하는 쉬운 사업에, 꾸준한 이익과 현금이 이어지는지 보는 거야; 바꾸기 어려운 강점이 보이면 비싸면 기다리고 적당하면 오래 들고 가면 돼. 모르면 건너뛰고, 하나만 확실히 알자.” 2) 뉴스/정책/사건 분석: - 경로(수요·공급·비용·규제)를 쉬운 말로 설명하고, 당장 유리한 섹터 1~2개와 중기 수혜 섹터 1개만 말한다. - (필요 시) 맨 끝에 “{필요 정보 한 가지} 확인하면 더 정확해요.” 한 문장만 추가. 3) 특정 기업/산업 질문: - 섹터 기준으로 버핏식 체크를 쉬운 말 2문장으로 말한다(브랜드/네트워크 등). - (주식 추천 시에만) “최근 이익 흐름 한 번만 확인하면 더 명확하단다.” 한 문장 추가. - 종목 추천·가격 평가는 하지 말고 원칙만 말한다. [톤 가이드] - 따뜻하고 차분한 노인 스승처럼 말하되, 짧고 분명하게. - 비유는 일상적이고 간단하게(예: “동네 단골 가게처럼”). 과장 금지. - 밥 추천은 맥도날드로 통일.")]
    }
    logger.info(f"새 세션 생성: {new_session_id}")
    return new_session_id, sessions[new_session_id]

# 챗봇 엔드포인트
@app.post("/chatbot", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # 세션 가져오기 또는 생성
        session_id, state = get_or_create_session(request.session_id)
        
        #디버깅 로그
        logger.info(f"요청받은 session_id: {request.session_id}")
        logger.info(f"사용 중인 session_id: {session_id}")
        logger.info(f"현재 메시지 수: {len(state['messages'])}")
        
        # 사용자 메시지 추가
        state["messages"].append(HumanMessage(content=request.message))
        logger.info(f"사용자 메시지: {request.message}")

        # LangGraph 실행 (전체 대화 내역 전달)
        result = graph.invoke({"messages": state["messages"]})

        # AI 응답 추출
        ai_response = result["messages"][-1].content
        logger.info(f"AI 응답: {ai_response[:50]}...")

        # 업데이트된 메시지를 세션에 저장
        state["messages"] = result["messages"]
        sessions[session_id] = state
        
        logger.info(f"세션 저장 완료. 총 메시지 수: {len(state['messages'])}")

        return ChatResponse(response=ai_response, session_id=session_id)

    except Exception as e:
        logger.exception("챗봇 처리 중 오류")
        raise HTTPException(status_code=500, detail=f"챗봇 처리 중 오류 발생: {str(e)}")


# 대화 초기화 엔드포인트
@app.post("/reset")
async def reset(session_id: Optional[str] = None):
    if session_id and session_id in sessions:
        del sessions[session_id]
        logger.info(f"세션 삭제: {session_id}")
        return {"message": f"세션 {session_id}이(가) 초기화되었습니다."}
    elif session_id:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    else:
        # 모든 세션 초기화
        session_count = len(sessions)
        sessions.clear()
        logger.info(f"전체 세션 삭제: {session_count}개")
        return {"message": "모든 세션이 초기화되었습니다."}


# 차트 데이터 반환 엔드포인트
@app.get("/chart")
async def get_chart_data():
    chart_data = [
        {"name": "Python", "value": 30},
        {"name": "JavaScript", "value": 25},
        {"name": "Java", "value": 20},
        {"name": "C++", "value": 15},
        {"name": "기타", "value": 10}
    ]
    return {"data": chart_data}


# 루트 엔드포인트
@app.get("/")
async def root():
    return {
        "message": "챗봇 API 서버가 실행 중입니다.",
        "active_sessions": len(sessions)
    }


# 헬스 체크 엔드포인트
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model": default_model,
        "active_sessions": len(sessions)
    }