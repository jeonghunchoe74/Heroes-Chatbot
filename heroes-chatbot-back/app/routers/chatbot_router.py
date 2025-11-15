"""FastAPI routes that expose the chatbot features.

The previous version of this module contained many optional fallbacks and
indirect imports.  That made it difficult to follow what was actually required
for a request to succeed.  The goal of this rewrite is to keep every step
explicit and easy to read so that anyone can reason about the behaviour without
chasing side effects.

The API surface stays the same, but each handler is now a short function that
moves in a straight line:

1. Validate the incoming payload with simple ``pydantic`` models.
2. Call the matching service layer helper.
3. Shape the response in a friendly format.

No background socket server or dynamic imports are involved anymore which makes
this file a good starting point for newcomers who want to understand the
project.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.chatbot_service import (
    generate_response,
    get_initial_message,
    get_or_create_session,
    reset_session,
)
from app.services.news_service import summarize_news

router = APIRouter()


class ChatMessage(BaseModel):
    """Simple payload used by the websocket compatibility endpoint."""

    room: str = "default"
    text: str
    guru_id: str = "buffett"
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response format shared by the legacy ``/message`` endpoint."""

    room: str
    text: str
    role: str = "assistant"
    session_id: str


class WebChatRequest(BaseModel):
    """Payload for the web client."""

    message: str
    guru_id: str = "buffett"
    session_id: Optional[str] = None


class WebChatResponse(BaseModel):
    """Response returned to the web client."""

    response: str
    responseText: Optional[str] = None
    message: Optional[str] = None
    text: Optional[str] = None
    content: Optional[str] = None
    answer: Optional[str] = None
    session_id: str


class AnalyzeRequest(BaseModel):
    """Request body used when the user presses the "분석하기" button."""

    guru_id: str = "buffett"
    query: Optional[str] = None
    articles: Optional[List[Dict[str, Any]]] = None
    content: Optional[str] = None


class ResetBody(BaseModel):
    """Optional body for ``/chatbot/reset``."""

    session_id: Optional[str] = None


_active_rooms: set[str] = {"default"}


def _normalize_guru(guru_id: Optional[str]) -> str:
    """Map loose inputs such as "warren" back to the known guru identifiers."""

    if not guru_id:
        return "buffett"
    normalized = guru_id.strip().lower()
    if normalized in {"buffet", "warren", "warren-buffet"}:
        return "buffett"
    return normalized


@router.post("/message", response_model=ChatResponse)
async def send_message(message: ChatMessage) -> ChatResponse:
    """Compatibility endpoint used by the legacy websocket front-end."""

    if not message.text or not message.text.strip():
        raise HTTPException(status_code=400, detail="메시지가 비어 있습니다.")

    guru_id = _normalize_guru(message.guru_id)
    reply, session_id = await generate_response(
        user_input=message.text,
        session_id=message.session_id,
        guru_id=guru_id,
    )

    _active_rooms.add(message.room or "default")
    return ChatResponse(room=message.room or "default", text=reply, session_id=session_id)


@router.get("/rooms")
async def get_chat_rooms() -> Dict[str, List[str]]:
    """Return the list of rooms that exchanged at least one message."""

    return {"rooms": sorted(_active_rooms)}


@router.get("/chatbot/init/{guru_id}")
async def init_session(guru_id: str) -> Dict[str, Any]:
    """Create a new session and fetch the landing copy for the selected mentor."""

    normalized = _normalize_guru(guru_id)
    session_id, _ = get_or_create_session(None, normalized)

    try:
        initial_payload = await get_initial_message(normalized)
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=500, detail=f"초기 메시지를 불러오지 못했습니다: {exc}") from exc

    intro = initial_payload.get("intro", "") if isinstance(initial_payload, dict) else ""
    news = initial_payload.get("news", []) if isinstance(initial_payload, dict) else []
    if not isinstance(news, list):
        news = []

    return {
        "ok": True,
        "guru_id": normalized,
        "session_id": session_id,
        "sessionId": session_id,  # backwards compatibility with the front-end
        "intro": intro,
        "news": news,
    }


@router.post("/chatbot", response_model=WebChatResponse)
@router.post("/chatbot/", response_model=WebChatResponse)
async def web_chat(request: WebChatRequest) -> WebChatResponse:
    """Main text conversation endpoint."""

    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="메시지가 비어 있습니다.")

    guru_id = _normalize_guru(request.guru_id)
    try:
        reply, session_id = await generate_response(
            user_input=request.message,
            session_id=request.session_id,
            guru_id=guru_id,
        )
    except Exception as exc:  # pragma: no cover - surface friendly error
        raise HTTPException(status_code=500, detail=f"챗봇 오류: {exc}") from exc

    return WebChatResponse(
        response=reply,
        responseText=reply,
        message=reply,
        text=reply,
        content=reply,
        answer=reply,
        session_id=session_id,
    )


async def _analyze_single_article(article: Dict[str, Any]) -> Dict[str, str]:
    """Analyse one article by delegating to the chatbot brain."""

    content = (article.get("content") or article.get("summary") or "").strip()
    guru_id = _normalize_guru(article.get("guru_id"))
    if not content:
        return {"analysis": "분석할 내용이 없습니다."}

    prompt = (
        f"[뉴스 분석 요청] 다음 뉴스 내용을 {guru_id}의 투자 관점으로 4~6문장으로 간결히 분석해줘.\n\n"
        "중요: 반드시 분석 내용에 다음 중 하나의 섹터 이름을 정확히 포함해야 합니다:\n"
        "반도체, 유틸리티, 금융서비스, 소프트웨어·서비스, 에너지, 소재, 자동차·부품, 통신서비스, 보험, 은행, 헬스케어 장비·서비스\n\n"
        "예시 형식:\n"
        "- '이 뉴스는 반도체 산업에 대한 것입니다...'\n"
        "- '금융서비스 업계의 주요 이슈를 다루고 있습니다...'\n"
        "- '은행 부문에서 중요한 변화가 있습니다...'\n\n"
        "섹터 이름은 반드시 분석 텍스트 본문에 포함되어야 합니다.\n\n"
        f"뉴스 내용:\n{content}"
    )

    reply, _ = await generate_response(user_input=prompt, session_id=None, guru_id=guru_id)
    
    # 디버깅: 응답에 섹터가 포함되는지 확인
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Analysis reply length: %d", len(reply) if reply else 0)
    logger.info("Analysis reply preview: %s", reply[:200] + "..." if reply and len(reply) > 200 else reply)
    
    # 섹터 확인
    from app.services.chatbot_service import _extract_sector_from_answer
    sector = _extract_sector_from_answer(reply)
    if sector:
        logger.info("Sector found in analysis reply: %s", sector)
    else:
        logger.warning("No sector found in analysis reply. Reply: %s", reply[:300])
    
    return {"analysis": reply}


@router.post("/chatbot/analyze")
async def analyze_news_api(request: AnalyzeRequest) -> Dict[str, Any]:
    """Handle the "분석하기" workflow used on the landing page."""

    # When the caller provides a direct article payload we only analyse that item.
    if (request.content and request.content.strip()) or (request.articles and len(request.articles) == 1):
        article_payload: Dict[str, Any] = {
            "guru_id": _normalize_guru(request.guru_id),
            "content": request.content or (request.articles[0].get("summary") if request.articles else ""),
        }
        analysis = await _analyze_single_article(article_payload)
        return {"ok": True, "guru_id": article_payload["guru_id"], **analysis}

    # 전체 뉴스에 대해 각각 섹터 분석 수행
    guru_id = _normalize_guru(request.guru_id)
    news_items = await summarize_news(guru_id) or []
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Analyzing %d news items for guru: %s", len(news_items), guru_id)

    if not news_items:
        return {
            "ok": True,
            "guru_id": guru_id,
            "analysis": "분석할 뉴스가 없습니다.",
            "news": []
        }

    # 각 뉴스 항목에 대해 섹터 분석 수행
    analysis_results: List[str] = []
    for index, item in enumerate(news_items, start=1):
        title = (item.get("title") or "").strip() if isinstance(item, dict) else ""
        description = (item.get("description") or item.get("summary") or "").strip() if isinstance(item, dict) else ""
        
        # 제목과 설명을 결합하여 분석에 사용 (더 많은 정보)
        if description:
            content = f"{title}\n\n{description}"
        else:
            content = title  # 설명이 없으면 제목만 사용
        
        if not content:
            continue
            
        logger.info("Analyzing news item %d: %s", index, title[:50])
        logger.debug("Content for analysis: %s", content[:100] + "..." if len(content) > 100 else content)
        
        try:
            article_payload: Dict[str, Any] = {
                "guru_id": guru_id,
                "content": content,
            }
            result = await _analyze_single_article(article_payload)
            analysis_text = result.get("analysis", "")
            
            if analysis_text:
                analysis_results.append(f"{index}. {title}\n   {analysis_text}")
                logger.info("Analysis completed for news item %d", index)
            else:
                logger.warning("No analysis result for news item %d", index)
        except Exception as exc:
            logger.error("Error analyzing news item %d: %s", index, exc, exc_info=True)
            # 오류가 발생해도 계속 진행
            analysis_results.append(f"{index}. {title}\n   (분석 중 오류가 발생했습니다)")

    if analysis_results:
        # 모든 분석 결과를 합침
        analysis_text = "📌 오늘의 뉴스 분석\n\n" + "\n\n".join(analysis_results)
    else:
        analysis_text = "뉴스 분석을 완료하지 못했습니다."

    return {"ok": True, "guru_id": guru_id, "analysis": analysis_text, "news": news_items}


@router.post("/chatbot/reset")
async def reset_session_api(body: Optional[ResetBody] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Reset a specific session or clear every stored conversation."""

    target_session = session_id or (body.session_id if body else None)
    message = reset_session(target_session)
    return {"ok": True, "message": message}