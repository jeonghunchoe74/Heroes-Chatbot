from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# =========================
# (안전) schemas 임포트
# =========================
try:
    from app.models.schemas import ChatMessage, ChatResponse
    _HAS_SCHEMAS = True
except Exception:
    _HAS_SCHEMAS = False

    class ChatMessage(BaseModel):
        room: Optional[str] = "default"
        text: str
        guru_id: Optional[str] = "buffett"
        session_id: Optional[str] = None

    class ChatResponse(BaseModel):
        room: Optional[str] = "default"
        text: str
        role: str = "assistant"
        session_id: str

# =========================
# (안전) ChatServer 임포트
# =========================
try:
    from app.sockets.chat_server import ChatServer
    _HAS_CHATSERVER = True
except Exception:
    _HAS_CHATSERVER = False
    ChatServer = None  # type: ignore

# =========================
# 서비스 임포트
# =========================
from app.services.chatbot_service import (
    generate_response,
    get_or_create_session,
    get_initial_message,
)
from app.services.news_service import summarize_news

# =========================
# 유틸
# =========================
def _normalize_guru(g: Optional[str]) -> str:
    g = (g or "buffett").strip().lower()
    return "buffett" if g in ("buffet", "warren", "warren-buffet") else g

# =========================
# ChatServer 폴백
# =========================
class MinimalChatServer:
    """
    ChatServer가 없을 때를 위한 최소 대체.
    /message 로 들어온 텍스트를 generate_response 로 처리.
    """
    def __init__(self):
        self._rooms: Dict[str, int] = {"default": 1}

    async def handle_message(self, message: ChatMessage) -> ChatResponse:
        if not message.text or not message.text.strip():
            raise HTTPException(status_code=400, detail="message.text is empty")

        gid = _normalize_guru(message.guru_id)
        sid_in = message.session_id
        if not sid_in:
            sid_in, _ = get_or_create_session(None, gid)

        try:
            ai, sid_out = await generate_response(
                user_input=message.text,
                session_id=sid_in,
                guru_id=gid,
            )
        except TypeError:
            ai, sid_out = await generate_response(message.text, sid_in, gid)  # type: ignore

        room = message.room or "default"
        self._rooms[room] = self._rooms.get(room, 0) + 1
        return ChatResponse(room=room, text=ai, role="assistant", session_id=sid_out)

    async def get_active_rooms(self) -> List[str]:
        return list(self._rooms.keys())

chat_server = ChatServer() if _HAS_CHATSERVER else MinimalChatServer()

# =========================
# (기존) /message, /rooms
# =========================
@router.post("/message", response_model=ChatResponse)
async def send_message(message: ChatMessage):
    try:
        message.guru_id = _normalize_guru(message.guru_id)
        return await chat_server.handle_message(message)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("send_message error")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rooms")
async def get_chat_rooms():
    try:
        rooms = await chat_server.get_active_rooms()
        return {"rooms": rooms}
    except Exception as e:
        logger.exception("get_chat_rooms error")
        raise HTTPException(status_code=500, detail=str(e))

# =========================
# (웹용) 모델
# =========================
class WebChatRequest(BaseModel):
    message: str
    guru_id: Optional[str] = "buffett"
    session_id: Optional[str] = None

class WebChatResponse(BaseModel):
    response: str
    responseText: Optional[str] = None
    message: Optional[str] = None
    text: Optional[str] = None
    content: Optional[str] = None
    answer: Optional[str] = None
    session_id: str

class AnalyzeRequest(BaseModel):
    guru_id: Optional[str] = "buffett"
    query: Optional[str] = None
    articles: Optional[List[Dict[str, Any]]] = None
    content: Optional[str] = None  # 프론트가 보내는 요약/본문(옵션)

class ResetBody(BaseModel):
    session_id: Optional[str] = None

# =========================
# 초기 데이터
# =========================
@router.get("/chatbot/init/{guru_id}")
async def init_session(guru_id: str):
    gid = _normalize_guru(guru_id)
    session_id, _ = get_or_create_session(session_id=None, guru_id=gid)
    try:
        initial = await get_initial_message(gid)
        intro = initial.get("intro", "") if isinstance(initial, dict) else ""
        news = initial.get("news", []) if isinstance(initial, dict) else []
        if not isinstance(news, list):
            news = []
    except Exception:
        logger.exception("get_initial_message failed")
        intro, news = "", []

    return {
        "ok": True,
        "guru_id": gid,
        "session_id": session_id,
        "sessionId": session_id,
        "intro": intro,
        "news": news,
    }

# =========================
# 채팅
# =========================
@router.post("/chatbot", response_model=WebChatResponse)
@router.post("/chatbot/", response_model=WebChatResponse)
async def web_chat(req: WebChatRequest):
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="메시지가 비어 있습니다.")

    gid = _normalize_guru(req.guru_id)
    try:
        ai, sid = await generate_response(
            user_input=req.message,
            session_id=req.session_id,
            guru_id=gid,
        )
    except Exception as e:
        logger.exception("web_chat error")
        raise HTTPException(status_code=500, detail=f"챗봇 오류: {str(e)}")

    return WebChatResponse(
        response=ai,
        responseText=ai,
        message=ai,
        text=ai,
        content=ai,
        answer=ai,
        session_id=sid,
    )

# =========================
# 기사 단건 분석 (섹터 감지는 generate_response 에서 1회만)
# =========================
async def analyze_article(data: dict):
    """
    특정 뉴스 기사 한 건을 분석.
    섹터 감지/종목 Top5 부착은 chatbot_service.generate_response 내부 로직이 자동 수행.
    """
    content = (data.get("content") or data.get("summary") or "").strip()
    guru_id = _normalize_guru(data.get("guru_id"))
    if not content:
        return {"analysis": "분석할 내용이 없습니다."}

    question = f"""
다음 뉴스 내용을 {guru_id}의 투자 관점으로 4~6문장으로 간결히 분석해줘.
반드시 아래 집합 중 '정확히 하나'의 섹터 라벨을 문장 안에 그대로 넣어:
[반도체, 유틸리티, 금융서비스, 소프트웨어·서비스, 에너지, 소재, 자동차·부품, 통신서비스, 보험, 은행, 헬스케어 장비·서비스]
뉴스:
{content}
"""
    ai_response, _ = await generate_response(question, None, guru_id)
    return {"analysis": ai_response}

# =========================
# 뉴스 분석 엔드포인트
# =========================
@router.post("/chatbot/analyze")
async def analyze_news_api(req: AnalyzeRequest):
    """
    - 프론트가 content(기사 요약/본문)를 보내면: 단건 분석 → 'analysis' 로 반환
    - content 없으면: '오늘의 뉴스 요약'을 'analysis' 로 반환
    """
    try:
        # 1) 단건 기사 분석
        if (req.content and req.content.strip()) or (req.articles and len(req.articles) == 1):
            data = {
                "guru_id": _normalize_guru(req.guru_id),
                "content": (req.content or (req.articles[0].get("summary") if isinstance(req.articles[0], dict) else "")),
            }
            result = await analyze_article(data)
            return {"ok": True, "guru_id": data["guru_id"], **result}

        # 2) 오늘의 뉴스 요약
        gid = _normalize_guru(req.guru_id)
        items = summarize_news(gid) or []

        lines = []
        for i, it in enumerate(items, 1):
            title = (it.get("title") or "").strip() if isinstance(it, dict) else ""
            summ  = (it.get("summary") or it.get("desc") or "").strip() if isinstance(it, dict) else ""
            if len(summ) > 200:
                summ = summ[:200].rstrip() + "…"
            lines.append(f"{i}. {title}\n   - {summ}" if summ else f"{i}. {title}")
        summary_text = "📌 오늘의 뉴스 요약\n" + "\n".join(lines) if lines else "분석할 뉴스가 없습니다."

        return {
            "ok": True,
            "guru_id": gid,
            "analysis": summary_text,  # 프론트가 읽는 키
            "news": items,
        }
    except Exception as e:
        logger.exception("analyze_news_api error")
        raise HTTPException(status_code=500, detail=str(e))

# =========================
# 리셋 (프론트가 body 로 session_id 보냄)
# =========================
@router.post("/chatbot/reset")
async def reset_session_api(body: Optional[ResetBody] = None, session_id: Optional[str] = None):
    from app.services.chatbot_service import reset_session as _reset
    sid = session_id or (body.session_id if body else None)
    msg = _reset(sid)
    return {"ok": True, "message": msg}
