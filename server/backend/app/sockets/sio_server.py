import os
import socketio
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.models.schemas import JoinQueuePayload, SendMessagePayload
from app.services.study_room_manager import room_manager
from app.services.guru_service import get_guru_prompt
from app.services.chatbot_service import generate_group_feedback

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_DEFAULT_MODEL = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o-mini")

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
socket_app = socketio.ASGIApp(sio)
NS = "/room"

@sio.event
async def connect(sid, environ):
    await sio.emit("connected", {"sid": sid}, to=sid)

@sio.event
async def disconnect(sid):
    room_manager.leave(sid)

@sio.on("join_queue", namespace=NS)
async def join_queue(sid, data):
    payload = JoinQueuePayload(**{**data, "sid": sid})
    # enqueue 호출 전후로 큐 길이를 가져오려면 manager에 헬퍼 추가해도 되지만,
    # 간단히 room이 안 만들어지면 "queued"에 guru/ticker만 보내던 걸 queue_count도 보내자.
    room = room_manager.enqueue(payload.guru_id, payload.ticker, sid, payload.user_id)
    if room:
        # ... (기존 로직 그대로)
        ...
    else:
        # ✅ 대기 상태 피드백(프런트 로그에서 확인)
        await sio.emit("queued", {
            "guru_id": payload.guru_id,
            "ticker": payload.ticker,
            # 간단 확인용: 같은 키의 대기열 길이 노출
            "queue_count_hint": sum(1 for _ in room_manager.waiting.get((payload.guru_id, payload.ticker), []))
        }, to=sid, namespace=NS)

@sio.on("join_room", namespace=NS)
async def join_room(sid, data):
    room_id = data.get("room_id")
    user_id = data.get("user_id", sid)
    state = room_manager.join_existing(room_id, sid, user_id)
    if not state:
        await sio.emit("error", {"detail": "room not found"}, to=sid, namespace=NS)
        return
    await sio.enter_room(sid, room_id, namespace=NS)
    await sio.emit("system", {"text": f"{user_id} joined"}, room=room_id, namespace=NS)

@sio.on("send_message", namespace=NS)
async def send_message(sid, data):
    """
    payload: {room_id, author, phase, deliver_to_bot, content}
    ON: mentor_feedback 생성 후 emit
    OFF: 저장 + message 브로드캐스트만
    """
    payload = SendMessagePayload(**data)
    room = room_manager.get_room(payload.room_id)
    if not room:
        await sio.emit("error", {"detail": "room not found"}, to=sid, namespace=NS)
        return

    async with room.lock:
        msg = room_manager.append_message(payload.room_id, payload.author, payload.phase, payload.content)
        await sio.emit("message", {
            "message_id": msg.message_id,
            "author": msg.author,
            "phase": msg.phase,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat()
        }, room=payload.room_id, namespace=NS)

        if payload.deliver_to_bot:
            recent = room_manager.latest_cycle(payload.room_id)

            if room.prompt_cache:
                bullets = []
                for m in recent:
                    tag = {"news_insight": "뉴스/인사이트",
                        "mentor_feedback": "멘토피드백",
                        "user_response": "사용자답변"}.get(m.phase, m.phase)
                    bullets.append(f"- [{tag}] {m.author}: {m.content}")
                llm = ChatOpenAI(api_key=OPENAI_API_KEY, model_name=OPENAI_DEFAULT_MODEL)
                resp = llm.invoke([
                    SystemMessage(content=room.prompt_cache),
                    HumanMessage(content=f"종목: {room.ticker}\n아래 최근 사이클을 가치투자 관점으로 코멘트/질문/액션 각 1줄만 생성해줘.\n" + "\n".join(bullets))
                ])
                feedback_text = resp.content.strip()
            else:
                feedback_text = generate_group_feedback(
                    room.guru_id, room.ticker,
                    recent_messages=[{"phase": m.phase, "author": m.author, "content": m.content} for m in recent]
                )

            fb = room_manager.append_message(payload.room_id, author=f"bot.{room.guru_id}",
                                            phase="mentor_feedback", content={"text": feedback_text})
            room_manager.set_phase(payload.room_id, "user_response")

            await sio.emit("mentor_feedback", {
                "message_id": fb.message_id,
                "author": f"bot.{room.guru_id}",
                "phase": fb.phase,
                "content": fb.content,
                "timestamp": fb.timestamp.isoformat()
            }, room=payload.room_id, namespace=NS)
