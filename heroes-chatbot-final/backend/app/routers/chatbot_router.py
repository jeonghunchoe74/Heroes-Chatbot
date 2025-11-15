"""Chatbot API router — 통합 버전

- 구(旧) 버전 기능:
  - /chatbot (간단 텍스트 입출력, ChatRequest/ChatResponse)
  - /chatbot/reset (세션 초기화)
  - /chatbot/chart (샘플 차트 데이터)
  - /chatbot/health (헬스체크)

- 신(新) 버전 기능:
  - /message (웹소켓 호환용 endpoint)
  - /rooms (활성 방 목록)
  - /chatbot/init/{guru_id} (멘토 초기 세션/뉴스)
  - /chatbot, /chatbot/ (웹 클라이언트용 메인 대화)
  - /chatbot/analyze (뉴스/텍스트 분석)
  - /chatbot/reset (세션 리셋, body+query 겸용)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.chatbot_service import (
    generate_response,
    get_initial_message,
    get_or_create_session,
    reset_session,
)
from app.services.news_service import summarize_news

# ─────────────────────────────────────────────
# 라우터 설정 (main.py에서 prefix=""로 include 예정)
# ─────────────────────────────────────────────
router = APIRouter(tags=["Chatbot"])


# ─────────────────────────────────────────────
# 구(旧) 버전: 단순 /chatbot API용 모델
# ─────────────────────────────────────────────
class SimpleChatRequest(BaseModel):
    message: str
    guru_id: Optional[str] = "buffett"
    session_id: Optional[str] = None


class SimpleChatResponse(BaseModel):
    response: str
    session_id: str


# ─────────────────────────────────────────────
# 신(新) 버전: 다양한 엔드포인트용 모델
# ─────────────────────────────────────────────
class ChatMessage(BaseModel):
    """웹소켓 호환 endpoint(/message)용"""

    room: str = "default"
    text: str
    guru_id: str = "buffett"
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """/message에서 사용하는 응답 포맷"""

    room: str
    text: str
    role: str = "assistant"
    session_id: str


class WebChatRequest(BaseModel):
    """현재 웹 프론트에서 주로 사용하는 /chatbot 바디"""

    message: str
    guru_id: str = "buffett"
    session_id: Optional[str] = None


class WebChatResponse(BaseModel):
    """웹 클라이언트용 응답 포맷 (여러 필드 이름 호환)"""

    response: str
    responseText: Optional[str] = None
    message: Optional[str] = None
    text: Optional[str] = None
    content: Optional[str] = None
    answer: Optional[str] = None
    session_id: str


class AnalyzeRequest(BaseModel):
    """분석하기 버튼용 바디 (/chatbot/analyze)"""

    guru_id: str = "buffett"
    query: Optional[str] = None
    articles: Optional[List[Dict[str, Any]]] = None
    content: Optional[str] = None


class ResetBody(BaseModel):
    """옵션 바디: /chatbot/reset"""

    session_id: Optional[str] = None


_active_rooms: set[str] = {"default"}


# ─────────────────────────────────────────────
# 내부 유틸
# ─────────────────────────────────────────────
def _normalize_guru(guru_id: Optional[str]) -> str:
    """느슨한 입력값을 정규화 (warren → buffett 등)"""

    if not guru_id:
        return "buffett"
    normalized = guru_id.strip().lower()
    if normalized in {"buffet", "warren", "warren-buffet"}:
        return "buffett"
    return normalized


# ─────────────────────────────────────────────
# 1. 구(旧) 버전과 호환되는 심플 /chatbot 엔드포인트
# ─────────────────────────────────────────────
@router.post("/chatbot/simple", response_model=SimpleChatResponse)
async def simple_chat(request: SimpleChatRequest):
    """
    옛날 버전에서 사용하던 단순 /chatbot 형태를 유지하기 위한 endpoint.
    (프론트에서 이 경로를 안 쓰면 무시해도 됨)
    """
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="메시지가 비어 있습니다.")

    guru_id = _normalize_guru(request.guru_id)
    try:
        ai_response, session_id = await generate_response(
            user_input=request.message,
            session_id=request.session_id,
            guru_id=guru_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"챗봇 오류: {str(e)}")

    return SimpleChatResponse(response=ai_response, session_id=session_id)


# ─────────────────────────────────────────────
# 2. 웹소켓 호환용 /message, /rooms
# ─────────────────────────────────────────────
@router.post("/message", response_model=ChatResponse)
async def send_message(message: ChatMessage) -> ChatResponse:
    """이전 웹소켓 프론트에서 사용하던 호환 endpoint."""

    if not message.text or not message.text.strip():
        raise HTTPException(status_code=400, detail="메시지가 비어 있습니다.")

    guru_id = _normalize_guru(message.guru_id)
    reply, session_id = await generate_response(
        user_input=message.text,
        session_id=message.session_id,
        guru_id=guru_id,
    )

    room = message.room or "default"
    _active_rooms.add(room)
    return ChatResponse(room=room, text=reply, session_id=session_id)


@router.get("/rooms")
async def get_chat_rooms() -> Dict[str, List[str]]:
    """메시지를 한 번이라도 주고받은 방 리스트"""

    return {"rooms": sorted(_active_rooms)}


# ─────────────────────────────────────────────
# 3. 멘토 선택 초기 세션 생성 + 뉴스
# ─────────────────────────────────────────────
@router.get("/chatbot/init/{guru_id}")
async def init_session(guru_id: str) -> Dict[str, Any]:
    """선택한 멘토 기준으로 세션 생성 + 초기 인트로·뉴스 반환"""

    normalized = _normalize_guru(guru_id)
    session_id, _ = get_or_create_session(None, normalized)

    try:
        initial_payload = await get_initial_message(normalized)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"초기 메시지를 불러오지 못했습니다: {exc}",
        ) from exc

    intro = initial_payload.get("intro", "") if isinstance(initial_payload, dict) else ""
    news = initial_payload.get("news", []) if isinstance(initial_payload, dict) else []
    if not isinstance(news, list):
        news = []

    return {
        "ok": True,
        "guru_id": normalized,
        "session_id": session_id,
        "sessionId": session_id,  # 프론트 호환
        "intro": intro,
        "news": news,
    }


# ─────────────────────────────────────────────
# 4. 메인 웹 대화 엔드포인트 (/chatbot, /chatbot/)
# ─────────────────────────────────────────────
@router.post("/chatbot", response_model=WebChatResponse)
@router.post("/chatbot/", response_model=WebChatResponse)
async def web_chat(request: WebChatRequest) -> WebChatResponse:
    """현재 사용하는 메인 텍스트 대화 endpoint."""

    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="메시지가 비어 있습니다.")

    guru_id = _normalize_guru(request.guru_id)
    try:
        reply, session_id = await generate_response(
            user_input=request.message,
            session_id=request.session_id,
            guru_id=guru_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"챗봇 오류: {exc}") from exc

    # 여러 키 이름으로 같은 내용을 내려서 프론트 호환 유지
    return WebChatResponse(
        response=reply,
        responseText=reply,
        message=reply,
        text=reply,
        content=reply,
        answer=reply,
        session_id=session_id,
    )


# ─────────────────────────────────────────────
# 5. 뉴스/텍스트 분석 (/chatbot/analyze)
# ─────────────────────────────────────────────
async def _analyze_single_article(article: Dict[str, Any]) -> Dict[str, str]:
    """단일 뉴스/텍스트에 대해 섹터 포함 분석 수행."""

    content = (article.get("content") or article.get("summary") or "").strip()
    guru_id = _normalize_guru(article.get("guru_id"))
    if not content:
        return {"analysis": "분석할 내용이 없습니다."}

    prompt = (
        f"[뉴스 분석 요청] 다음 뉴스 내용을 {guru_id}의 투자 관점으로 4~6문장으로 간결히 분석해줘.\n\n"
        "중요: 반드시 분석 내용에 다음 중 하나의 섹터 이름을 정확히 포함해야 합니다:\n"
        "반도체, 유틸리티, 금융서비스, 소프트웨어·서비스, 에너지, 소재, 자동차·부품, 통신서비스, 보험, 은행, "
        "헬스케어 장비·서비스\n\n"
        "예시 형식:\n"
        "- '이 뉴스는 반도체 산업에 대한 것입니다...'\n"
        "- '금융서비스 업계의 주요 이슈를 다루고 있습니다...'\n"
        "- '은행 부문에서 중요한 변화가 있습니다...'\n\n"
        "섹터 이름은 반드시 분석 텍스트 본문에 포함되어야 합니다.\n\n"
        f"뉴스 내용:\n{content}"
    )

    reply, _ = await generate_response(user_input=prompt, session_id=None, guru_id=guru_id)

    # 디버깅용 로그
    import logging

    logger = logging.getLogger(__name__)
    logger.info("Analysis reply length: %d", len(reply) if reply else 0)
    logger.info(
        "Analysis reply preview: %s",
        reply[:200] + "..." if reply and len(reply) > 200 else reply,
    )

    # 섹터 추출 (없어도 기능에는 지장 없음)
    try:
        from app.services.chatbot_service import _extract_sector_from_answer

        sector = _extract_sector_from_answer(reply)
        if sector:
            logger.info("Sector found in analysis reply: %s", sector)
        else:
            logger.warning("No sector found in analysis reply. Reply: %s", reply[:300])
    except Exception:
        # 내부 헬퍼 없을 때도 전체 흐름은 유지
        logger.warning("Sector extraction helper not available.")

    return {"analysis": reply}


@router.post("/chatbot/analyze")
async def analyze_news_api(request: AnalyzeRequest) -> Dict[str, Any]:
    """랜딩 페이지/바텀시트에서 사용하는 '분석하기' 플로우."""

    # 1) 프론트에서 직접 content 또는 단일 article을 보낸 경우
    if (request.content and request.content.strip()) or (
        request.articles and len(request.articles) == 1
    ):
        article_payload: Dict[str, Any] = {
            "guru_id": _normalize_guru(request.guru_id),
            "content": request.content
            or (request.articles[0].get("summary") if request.articles else ""),
        }
        analysis = await _analyze_single_article(article_payload)
        return {"ok": True, "guru_id": article_payload["guru_id"], **analysis}

    # 2) 서버에서 최신 뉴스 가져와서 일괄 분석
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
            "news": [],
        }

    analysis_results: List[str] = []
    for index, item in enumerate(news_items, start=1):
        title = (item.get("title") or "").strip() if isinstance(item, dict) else ""
        description = (
            (item.get("description") or item.get("summary") or "").strip()
            if isinstance(item, dict)
            else ""
        )

        if description:
            content = f"{title}\n\n{description}"
        else:
            content = title

        if not content:
            continue

        logger.info("Analyzing news item %d: %s", index, title[:50])

        try:
            article_payload = {"guru_id": guru_id, "content": content}
            result = await _analyze_single_article(article_payload)
            analysis_text = result.get("analysis", "")

            if analysis_text:
                analysis_results.append(f"{index}. {title}\n   {analysis_text}")
                logger.info("Analysis completed for news item %d", index)
            else:
                logger.warning("No analysis result for news item %d", index)
        except Exception as exc:
            logger.error(
                "Error analyzing news item %d: %s", index, exc, exc_info=True
            )
            analysis_results.append(
                f"{index}. {title}\n   (분석 중 오류가 발생했습니다)"
            )

    if analysis_results:
        analysis_text = "📌 오늘의 뉴스 분석\n\n" + "\n\n".join(analysis_results)
    else:
        analysis_text = "뉴스 분석을 완료하지 못했습니다."

    return {"ok": True, "guru_id": guru_id, "analysis": analysis_text, "news": news_items}


# ─────────────────────────────────────────────
# 6. 세션 리셋 (/chatbot/reset) — 구/신 버전 모두 호환
# ─────────────────────────────────────────────
@router.post("/chatbot/reset")
async def reset_session_api(
    body: Optional[ResetBody] = None,
    session_id: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    """
    세션 전체/부분 초기화.
    - 구 버전: /chatbot/reset?session_id=...  → {"message": "..."}
    - 신 버전: body.session_id 사용          → {"ok": True, "message": "..."}
    """

    target_session = session_id or (body.session_id if body else None)
    message = reset_session(target_session)
    return {"ok": True, "message": message}


# ─────────────────────────────────────────────
# 7. 샘플 차트 데이터 + 헬스 체크 (구 버전 기능)
# ─────────────────────────────────────────────
@router.get("/chatbot/chart")
async def get_chart_data():
    chart_data = [
        {"name": "Python", "value": 30},
        {"name": "JavaScript", "value": 25},
        {"name": "Java", "value": 20},
        {"name": "C++", "value": 15},
        {"name": "기타", "value": 10},
    ]
    return {"data": chart_data}


@router.get("/chatbot/health")
async def health_check():
    return {"status": "healthy"}
