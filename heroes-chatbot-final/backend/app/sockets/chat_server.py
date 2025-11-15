# app/sockets/chat_server.py
import os
import re
import time
import uuid
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx
import socketio

from app.core.config import settings
from app.services import file_service
from app.core.redis import redis
from app.services.insight_cache import (
    get_or_create_thread,
    append_message,
    load_messages,
)
import json
from app.utils.link_preview import extract_urls, fetch_og

# Socket.IO 서버 (ASGI 모드)
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
)

ROOM = "lobby"
# FastAPI의 챗봇 REST 엔드포인트
CHATBOT_URL = os.getenv("CHATBOT_URL", "http://127.0.0.1:8000/chatbot/")
CHATBOT_RESET_URL = os.getenv("CHATBOT_RESET_URL", "http://127.0.0.1:8000/chatbot/reset")

GURU_ALIASES = {
    "wood": "ark",
    "cathie": "ark",
    "lynch": "lynch",
    "peter": "lynch",
    "buffett": "buffett",
    "warren": "buffett",
    "ark": "ark",
}

GURU_LABELS = {
    "buffett": "워렌 버핏",
    "lynch": "피터 린치",
    "ark": "캐시 우드",
}


def _normalize_guru(guru_id: str | None) -> str | None:
    if not guru_id:
        return None
    gid = guru_id.lower()
    gid = GURU_ALIASES.get(gid, gid)
    return gid if gid in GURU_LABELS else None


def _guru_label(guru_id: str) -> str:
    return GURU_LABELS.get(guru_id, guru_id.title())


room_guru = _normalize_guru(os.getenv("ROOM_GURU")) or "buffett"
MENTOR_DEFAULT_ENABLED = os.getenv("MENTOR_DEFAULT_ENABLED", "true").lower() != "false"
mentor_enabled = MENTOR_DEFAULT_ENABLED
user_meta: dict[str, dict[str, str]] = {}

PUBLIC_BASE_URL = settings.PUBLIC_BASE_URL
UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads"


async def _request_chatbot_response(message: str, guru: str, room: str = ROOM) -> str:
    session_id = f"{room}::{guru}"
    payload = {"guru_id": guru, "session_id": session_id, "message": message}
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.post(CHATBOT_URL, json=payload)
        response.raise_for_status()
        if response.headers.get("content-type", "").startswith("application/json"):
            data = response.json()
            return (
                data.get("answer")
                or data.get("response")
                or data.get("message")
                or ""
            )
        return response.text


def get_user_room(sid: str) -> str:
    meta = user_meta.get(sid) or {}
    return meta.get("room") or ROOM


def get_sio_app(fastapi_app):
    """
    FastAPI 앱을 Socket.IO ASGIApp으로 래핑해 한 덩어리로 서빙.
    socketio_path는 최종 경로의 '끝부분'만 적는다.
    여기서 'ws/socket.io'로 지정했으므로 접속 경로는 /ws/socket.io 가 된다.
    """
    return socketio.ASGIApp(
        sio,
        other_asgi_app=fastapi_app,
        socketio_path="ws/socket.io",
    )


async def analyze_file_with_ai(meta: dict):
    """
    업로드된 파일 메타를 기반으로 AI 분석 수행.
    - mentor_enabled가 꺼져 있으면 아무 것도 하지 않음
    - PDF면 전체 텍스트(meta.full_text)를 우선 사용하여 상세 분석
    - 아니면 preview 텍스트로 요약
    """
    if not mentor_enabled:
        return
    try:
        # 방/유저 정보 추출
        sid = meta.get("sid") or "http"
        session = None
        room_name = ROOM
        try:
            session = await sio.get_session(sid) if sid and sid != "http" else {}
        except Exception:
            session = {}
        room_name = (session or {}).get("room") or get_user_room(sid) if sid else ROOM
        guru = room_guru

        name = meta.get("name") or ""
        mime = (meta.get("mime") or "").lower()
        ext = (Path(meta.get("id") or "").suffix or "").lower()

        full_text = (meta.get("full_text") or "").strip()
        preview = (meta.get("preview") or "").strip()

        text_for_ai = ""
        if "pdf" in mime or ext == ".pdf":
            text_for_ai = full_text or preview
        else:
            text_for_ai = preview or full_text

        if not text_for_ai:
            return

        if "pdf" in mime or ext == ".pdf":
            prompt = (
                "[업로드된 PDF 문서 분석]\n"
                f"파일명: {name}\n"
                "다음은 문서의 전체(또는 대부분) 본문입니다. 핵심 요점, 구조 요약, 중요한 수치/항목을 간결히 정리해줘.\n\n"
                f"{text_for_ai}"
            )
        else:
            prompt = (
                "[업로드 파일 요약]\n"
                f"파일명: {name}\n"
                "다음 텍스트를 5줄 내로 요약해줘.\n\n"
                f"{text_for_ai}"
            )

        ai_text = await _request_chatbot_response(prompt, guru, room_name)
        await sio.emit(
            "chat_message",
            {
                "type": "chat",
                # 🔁 옛 버전 호환용 필드
                "user": guru,
                "text": ai_text,
                "msg": {
                    "text": ai_text,
                    "sender": {"sid": "ai", "name": guru},
                    "ts": int(time.time() * 1000),
                },
            },
            room=room_name,
        )
    except Exception as e:
        try:
            await sio.emit("system", {"text": f"파일 분석 오류: {e}"}, room=room_name if 'room_name' in locals() else ROOM)
        except Exception:
            pass


@sio.event
async def connect(sid, environ):
    print(f"✅ User connected: {sid}")
    await sio.enter_room(sid, ROOM)
    await _announce_guru(to_sid=sid)
    await _announce_mentor_enabled(to_sid=sid)
    await _broadcast_lobby_count()


@sio.event
async def join_lobby(sid, data):
    name = (data or {}).get("name", "누군가")
    # await sio.emit("system", {"text": f"{name} 입장"}, room=ROOM)
    await _announce_guru(to_sid=sid, system_message=False)
    await _announce_mentor_enabled(to_sid=sid, system_message=False)
    await _broadcast_lobby_count()


@sio.event
async def join_room(sid, data):
    room_name = (data or {}).get("room") or ROOM
    name = (data or {}).get("name") or "익명"

    user_meta[sid] = {"name": name, "room": room_name}
    await sio.save_session(sid, {"name": name, "room": room_name})

    try:
        for existing in list(sio.rooms(sid)):
            if existing in {sid, ROOM, room_name}:
                continue
            await sio.leave_room(sid, existing)
    except Exception:
        pass

    await sio.enter_room(sid, room_name)
    await sio.emit("system", {"text": f"{name} 님이 입장했습니다."}, room=room_name)
    await _announce_guru(to_sid=sid, system_message=False, room=room_name)
    await _announce_mentor_enabled(to_sid=sid, system_message=False, room=room_name)
    await _broadcast_lobby_count(room=room_name)


@sio.event
async def chat_message(sid, data):
    """
    메인 채팅 메시지 이벤트.

    - 새 프론트: msg.sender / msg.text / type="chat" 사용
    - 옛 프론트: user / text 필드 사용 → 둘 다 포함해서 내보냄
    """
    payload = data or {}
    text = payload.get("message") or ""
    user_hint = payload.get("user") or "익명"

    session = await sio.get_session(sid)
    session = session or {}
    room_name = payload.get("room") or session.get("room") or get_user_room(sid)
    user_name = session.get("name") or user_hint
    user_meta[sid] = {"name": user_name, "room": room_name}

    # ❗클라이언트의 멘토 선택은 무시하고, 방 멘토만 사용 (현재 단일 상태 공유)
    guru = room_guru

    # 1) 사용자 메시지 에코
    await sio.emit(
        "chat_message",
        {
            "type": "chat",
            # 🔁 옛 버전 호환용 필드
            "user": user_name,
            "text": text,
            "msg": {
                "text": text,
                "sender": {"sid": sid, "name": user_name},
            },
        },
        room=room_name,
    )

    urls = extract_urls(text)
    link_meta_for_ai: Optional[dict] = None
    if urls and settings.LINK_FETCH_ENABLED:
        for url in urls:
            try:
                meta = _resolve_internal_file(url)
                if not meta:
                    meta = await fetch_og(url)

                if not meta:
                    continue

                if settings.LINK_PREVIEW_EMIT:
                    payload_meta = {
                        "id": uuid.uuid4().hex,
                        "url": meta.get("url"),
                        "host": meta.get("host"),
                        "site_name": meta.get("site_name"),
                        "title": meta.get("title"),
                        "description": meta.get("description"),
                        "image": meta.get("image"),
                        "ownerSid": sid,
                        "ownerName": user_name,
                    }
                    await sio.emit("link_preview", payload_meta, room=room_name)

                if mentor_enabled and not link_meta_for_ai and meta.get("text"):
                    link_meta_for_ai = meta
            except Exception as e:
                await sio.emit("system", {"text": f"링크 처리 실패: {e}"}, room=room_name)

    if not mentor_enabled:
        return

    if link_meta_for_ai:
        try:
            prompt = _build_link_prompt(link_meta_for_ai)
            ai_text = await _request_chatbot_response(prompt, guru, room_name)
            await sio.emit(
                "chat_message",
                {
                    "type": "chat",
                    # 🔁 옛 버전 호환용 필드
                    "user": guru,
                    "text": ai_text,
                    "msg": {
                        "text": ai_text,
                        "sender": {"sid": "ai", "name": guru},
                    },
                },
                room=room_name,
            )
            return
        except Exception as e:
            await sio.emit("system", {"text": f"링크 처리 실패: {e}"}, room=room_name)

    # 2) 챗봇 호출 → 동일 스키마로 브로드캐스트 (링크 본문을 확보하지 못한 경우)
    try:
        ai_text = await _request_chatbot_response(text, guru, room_name)
        await sio.emit(
            "chat_message",
            {
                "type": "chat",
                # 🔁 옛 버전 호환용 필드
                "user": guru,
                "text": ai_text,
                "msg": {
                    "text": ai_text,
                    "sender": {"sid": "ai", "name": guru},
                },
            },
            room=room_name,
        )

    except Exception as e:
        await sio.emit("system", {"text": f"AI 응답 오류: {e}"}, room=room_name)


@sio.event
async def disconnect(sid):
    meta = user_meta.pop(sid, None) or {}
    room_name = meta.get("room") or ROOM
    name = meta.get("name") or "누군가"

    print(f"❌ User disconnected: {sid}")
    await sio.emit("system", {"text": f"{name} 님이 퇴장했습니다."}, room=room_name)
    await _broadcast_lobby_count(room=room_name)

    try:
        await sio.leave_room(sid, room_name)
    except Exception:
        pass
    try:
        await sio.leave_room(sid, ROOM)
    except Exception:
        pass


# --- helpers ---
async def _broadcast_lobby_count(*, room: str | None = None):
    try:
        target_room = room or ROOM
        rooms_by_ns = sio.manager.rooms
        room_set = None
        if isinstance(rooms_by_ns, dict):
            room_set = rooms_by_ns.get("/", {}).get(target_room) or rooms_by_ns.get(None, {}).get(
                target_room
            )
        count = len(room_set) if room_set else 0
        await sio.emit("lobby_stats", {"count": count}, room=target_room)
    except Exception:
        pass


async def _announce_guru(
    *, to_sid: str | None = None, system_message: bool = True, room: str | None = None
):
    payload = {"guruId": room_guru, "label": _guru_label(room_guru)}
    emit_kwargs = {"to": to_sid} if to_sid else {"room": room or ROOM}
    if system_message:
        await sio.emit(
            "system",
            {"text": f"현재 멘토는 {payload['label']} 입니다."},
            **emit_kwargs,
        )
    await sio.emit("room_guru_changed", payload, **emit_kwargs)


async def _reset_chat_session(guru_id: str):
    """선택: 멘토 변경 시 기존 세션 초기화."""
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            await client.post(CHATBOT_RESET_URL, json={"session_id": f"{ROOM}::{guru_id}"})
    except Exception:
        # 리셋 실패는 치명적이지 않으므로 무시
        pass


@sio.event
async def set_room_guru(sid, data):
    requested = _normalize_guru((data or {}).get("guruId"))
    if not requested:
        return
    global room_guru
    session = await sio.get_session(sid)
    session = session or {}
    room_name = (data or {}).get("room") or session.get("room") or get_user_room(sid)
    if requested == room_guru:
        await _announce_guru(to_sid=sid, system_message=False, room=room_name)
        return
    room_guru = requested
    await _reset_chat_session(room_guru)
    await _announce_guru(room=room_name)


async def _announce_mentor_enabled(
    *, to_sid: str | None = None, system_message: bool = True, room: str | None = None
):
    emit_kwargs = {"to": to_sid} if to_sid else {"room": room or ROOM}
    await sio.emit("mentor_enabled_changed", {"enabled": mentor_enabled}, **emit_kwargs)
    if system_message:
        txt = "멘토 응답이 활성화되었습니다." if mentor_enabled else "멘토 응답이 비활성화되었습니다."
        await sio.emit("system", {"text": txt}, **emit_kwargs)


@sio.event
async def set_mentor_enabled(sid, data):
    global mentor_enabled
    enabled = bool((data or {}).get("enabled"))
    session = await sio.get_session(sid)
    session = session or {}
    room_name = (data or {}).get("room") or session.get("room") or get_user_room(sid)
    if enabled == mentor_enabled:
        await _announce_mentor_enabled(to_sid=sid, system_message=False, room=room_name)
        return
    mentor_enabled = enabled
    await _announce_mentor_enabled(room=room_name)


@sio.event
async def share_file(sid, data):
    meta = data or {}
    sender_name = meta.get("user") or "익명"
    timestamp = int(time.time() * 1000)
    session = await sio.get_session(sid)
    session = session or {}
    room_name = session.get("room") or get_user_room(sid)

    await sio.emit(
        "file_shared",
        {
            "type": "file",
            "msg": {
                "sender": {"sid": sid, "name": sender_name},
                "ownerSid": sid,
                "file": {
                    "id": meta.get("id"),
                    "name": meta.get("name"),
                    "size": meta.get("size"),
                    "mime": meta.get("mime"),
                    "url": meta.get("url"),
                },
                "preview": meta.get("preview") or "",
                "ts": timestamp,
            },
        },
        room=room_name,
    )

    if mentor_enabled and meta.get("preview"):
        try:
            guru = room_guru
            intro = (
                "[업로드 파일 요약 요청]\n"
                f"파일명: {meta.get('name')}\n"
                f"미리보기:\n{meta.get('preview')}\n\n"
                "핵심 포인트를 5줄 내로 정리해줘."
            )
            ai_text = await _request_chatbot_response(intro, guru, room_name)
            await sio.emit(
                "chat_message",
                {
                    "type": "chat",
                    # 🔁 옛 버전 호환용 필드
                    "user": guru,
                    "text": ai_text,
                    "msg": {
                        "text": ai_text,
                        "sender": {"sid": "ai", "name": guru},
                        "ts": int(time.time() * 1000),
                    },
                },
                room=room_name,
            )
        except Exception as e:
            await sio.emit("system", {"text": f"파일 요약 오류: {e}"}, room=room_name)


# =========================
# Thread (개별 바텀시트) 채팅
# =========================
@sio.event
async def thread_open(sid, data):
    """
    바텀시트를 열 때 호출.
    - Redis에서 스레드 메타/히스토리를 로딩해 요청자에게 thread_history 전송
    """
    try:
        session = await sio.get_session(sid)
        session = session or {}
        room_name = session.get("room") or get_user_room(sid)
        user_name = session.get("name") or "익명"
        guru = room_guru

        thread_key = (data or {}).get("threadKey") or ""
        meta = (data or {}).get("meta") or {}
        if not thread_key:
            return

        owner_sid = (meta.get("ownerSid") if isinstance(meta, dict) else None) or sid
        owner_name = (meta.get("ownerName") if isinstance(meta, dict) else None) or user_name

        # 스레드 메타 생성/조회
        info = await get_or_create_thread(
            thread_key,
            init_meta={**meta, "type": (data or {}).get("type")},
            room=room_name,
            guru_id=guru,
            owner_sid=owner_sid,
            owner_name=owner_name,
        )

        # 히스토리 로드 후 요청자에게만 전송
        messages = await load_messages(thread_key)
        await sio.emit(
            "thread_history",
            {"threadKey": thread_key, "messages": messages},
            to=sid,
        )
    except Exception as e:
        try:
            await sio.emit("system", {"text": f"스레드 시작 오류: {e}"}, room=room_name if 'room_name' in locals() else ROOM)
        except Exception:
            pass


@sio.event
async def thread_message(sid, data):
    """
    스레드 내부 사용자 메시지. 메인 톡방으로는 내보내지 않음.
    그대로 현재 방에 thread_message 이벤트로 브로드캐스트.
    """
    payload = data or {}
    text = payload.get("text") or ""
    thread_key = payload.get("threadKey") or ""
    if not text or not thread_key:
        return

    session = await sio.get_session(sid)
    session = session or {}
    room_name = session.get("room") or get_user_room(sid)
    user_name = session.get("name") or "익명"

    # 권한 체크 (업로더만)
    info = await redis.hgetall(f"thread:{thread_key}")
    if not info:
        return
    owner_sid = info.get("owner_sid")
    if owner_sid and owner_sid != sid:
        return

    # 사용자 메시지 기록
    user_msg = {
        "role": "user",
        "sid": sid,
        "name": user_name,
        "text": text,
        "ts": int(time.time() * 1000),
    }
    await append_message(thread_key, user_msg)
    await sio.emit(
        "thread_message",
        {"type": "thread", "msg": {**user_msg, "threadKey": thread_key}},
        room=room_name,
    )

    # AI 응답 생성
    guru = info.get("guru_id") or room_guru
    try:
        ai_text = await _request_chatbot_response(text, guru, room_name)
    except Exception as e:
        await sio.emit("system", {"text": f"AI 응답 오류: {e}"}, room=room_name)
        return
    ai_msg = {
        "role": "assistant",
        "sid": "ai",
        "name": guru,
        "text": ai_text,
        "ts": int(time.time() * 1000),
    }
    await append_message(thread_key, ai_msg)
    await sio.emit(
        "thread_message",
        {"type": "thread", "msg": {**ai_msg, "threadKey": thread_key}},
        room=room_name,
    )


def _build_public_file_url(path: str) -> str:
    if PUBLIC_BASE_URL:
        return f"{PUBLIC_BASE_URL}{path}"
    return path


def _shorten_preview(text: str, limit: int = 280) -> str | None:
    if not text:
        return None
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return None
    if len(normalized) > limit:
        return normalized[:limit].rstrip() + "…"
    return normalized


def _resolve_internal_file(url: str) -> Optional[dict]:
    parsed = urlparse(url)
    base_parsed = urlparse(PUBLIC_BASE_URL) if PUBLIC_BASE_URL else None
    base_host = base_parsed.hostname if base_parsed else ""
    host = parsed.hostname or ""

    if base_host:
        if host and host != base_host:
            return None
    elif host and host not in {"localhost", "127.0.0.1"}:
        return None

    path = parsed.path or ""
    if not path.startswith("/files/"):
        return None
    file_id = path[len("/files/") :]
    file_name = Path(file_id).name
    if not file_name:
        return None

    local_path = UPLOAD_DIR / file_name
    if not local_path.exists():
        return None

    text = file_service.extract_text_preview(local_path)
    preview_text = _shorten_preview(text, limit=280)
    public_url = _build_public_file_url(f"/files/{file_name}")
    public_host = urlparse(public_url).hostname or "local"

    return {
        "url": public_url,
        "host": public_host,
        "site_name": public_host if public_host != "local" else "Uploaded File",
        "title": file_name,
        "description": preview_text,
        "image": None,
        "text": text or None,
    }


def _build_link_prompt(meta: dict) -> str:
    title = meta.get("title") or meta.get("site_name") or meta.get("host") or "링크"
    url = meta.get("url") or ""
    text = meta.get("text") or ""
    return (
        "[링크 본문]\n"
        f"제목: {title}\n"
        f"URL: {url}\n"
        "본문:\n"
        f"{text}"
    )


def _truncate(text: str, limit: int = 2000) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def _build_thread_prompt_from_info(info: dict, user_text: str) -> str:
    """
    스레드 메타 정보를 바탕으로, 해당 스레드(뉴스/파일)에 대한 컨텍스트를 포함한 프롬프트 생성.
    """
    try:
        meta_json_raw = info.get("meta_json") or "{}"
        meta = json.loads(meta_json_raw)
    except Exception:
        meta = {}
    thread_type = (info.get("type") or "").lower()

    if thread_type == "preview":
        url = meta.get("url") or ""
        title = meta.get("title") or meta.get("site_name") or meta.get("host") or url
        description = meta.get("description") or ""
        body_text = ""
        # 뉴스 본문은 초기 미리보기 payload에 포함되지 않을 수 있어, 서버에서 재조회
        try:
            if url:
                og = fetch_og(url)
                body_text = og.get("text") or ""
        except Exception:
            body_text = ""
        body_text = _truncate(body_text, 1800)
        return (
            "[뉴스 스레드 컨텍스트]\n"
            f"제목: {title}\n"
            f"URL: {url}\n"
            f"요약: {description}\n"
            f"본문 발췌:\n{body_text}\n\n"
            f"[사용자 질문]\n{user_text}"
        )

    if thread_type == "file":
        file_meta = meta.get("file") or {}
        file_name = file_meta.get("name") or meta.get("name") or ""
        file_url = file_meta.get("url") or meta.get("url") or ""
        file_id = file_meta.get("id") or meta.get("id") or ""
        preview = meta.get("preview") or ""

        # 파일 로컬 경로 추정
        local_name = ""
        if file_url and "/files/" in file_url:
            local_name = file_url.split("/files/", 1)[-1]
        elif file_id:
            local_name = file_id
        full_text = ""
        try:
            if local_name:
                local_path = UPLOAD_DIR / Path(local_name).name
                if local_path.exists():
                    full_text = file_service.extract_full_text(local_path)
        except Exception:
            full_text = ""
        if not full_text and preview:
            full_text = preview
        full_text = _truncate(full_text, 1800)
        return (
            "[파일 스레드 컨텍스트]\n"
            f"파일명: {file_name}\n"
            f"URL: {file_url}\n"
            f"본문/요약 발췌:\n{full_text}\n\n"
            f"[사용자 질문]\n{user_text}"
        )

    # 알 수 없는 타입: 사용자 질문만 전달
    return user_text
