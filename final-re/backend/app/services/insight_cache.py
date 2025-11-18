import json
import time
import uuid
from typing import Any, Dict, List, Optional

from app.core.redis import redis

THREAD_TTL_SEC = 60 * 60 * 24 * 3  # 3일


def _meta_key(thread_key: str) -> str:
    return f"thread:{thread_key}"


def _msgs_key(thread_key: str) -> str:
    return f"thread:{thread_key}:msgs"


def _now_ms() -> int:
    return int(time.time() * 1000)


async def get_or_create_thread(
    thread_key: str,
    init_meta: Optional[Dict[str, Any]],
    room: str,
    guru_id: str,
    owner_sid: Optional[str] = None,
    owner_name: Optional[str] = None,
) -> Dict[str, Any]:
    """스레드 메타를 조회하거나 없으면 생성해서 반환."""
    meta_key = _meta_key(thread_key)
    info = await redis.hgetall(meta_key)
    if info:
        return info

    session_id = uuid.uuid4().hex
    meta_json = json.dumps(init_meta or {}, ensure_ascii=False)
    data = {
        "room": room,
        "owner_sid": owner_sid or "",
        "owner_name": owner_name or "",
        "guru_id": guru_id,
        "session_id": session_id,
        "type": (init_meta or {}).get("type") or "",
        "meta_json": meta_json,
        "created_ts": str(_now_ms()),
    }
    if owner_sid:
        data["owner_sid"] = owner_sid
    if owner_name:
        data["owner_name"] = owner_name

    if data.get("type") == "" and init_meta and ("file" in init_meta or "url" in init_meta):
        data["type"] = "file" if "file" in init_meta else "preview"

    await redis.hset(meta_key, mapping=data)
    await redis.expire(meta_key, THREAD_TTL_SEC)
    # 메시지 리스트 키도 TTL 부여
    await redis.expire(_msgs_key(thread_key), THREAD_TTL_SEC)
    return data


async def append_message(thread_key: str, msg: Dict[str, Any]) -> None:
    """메시지를 Redis 리스트에 추가하고 TTL을 갱신."""
    await redis.rpush(_msgs_key(thread_key), json.dumps(msg, ensure_ascii=False))
    await redis.expire(_msgs_key(thread_key), THREAD_TTL_SEC)
    await redis.expire(_meta_key(thread_key), THREAD_TTL_SEC)


async def load_messages(thread_key: str) -> List[Dict[str, Any]]:
    raw = await redis.lrange(_msgs_key(thread_key), 0, -1)
    out: List[Dict[str, Any]] = []
    for s in raw:
        try:
            out.append(json.loads(s))
        except Exception:
            continue
    return out

