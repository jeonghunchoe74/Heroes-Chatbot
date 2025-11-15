# app/core/redis.py

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class InMemoryRedis:
    """
    아주 간단한 Redis 대체용 클래스.
    - hgetall / hset : dict로 해시 흉내
    - rpush / lrange : list로 리스트 흉내
    - set / get      : key-value 흉내
    - expire         : TTL 설정은 무시하고 형식만 유지
    실제 Redis 서버는 전혀 안 쓰고, 파이썬 메모리 안에서만 동작함.
    """

    def __init__(self) -> None:
        self.hashes: Dict[str, Dict[str, str]] = {}
        self.lists: Dict[str, List[str]] = {}
        self.kv: Dict[str, str] = {}

    # ---- Hash 계열 ----
    async def hgetall(self, key: str) -> Dict[str, str]:
        return self.hashes.get(key, {}).copy()

    async def hset(self, key: str, mapping=None, **kwargs) -> int:
        if key not in self.hashes:
            self.hashes[key] = {}
        if mapping:
            for k, v in mapping.items():
                self.hashes[key][str(k)] = str(v)
        for k, v in kwargs.items():
            self.hashes[key][str(k)] = str(v)
        return 1

    # ---- List 계열 ----
    async def rpush(self, key: str, *values) -> int:
        lst = self.lists.setdefault(key, [])
        for v in values:
            lst.append(str(v))
        return len(lst)

    async def lrange(self, key: str, start: int, stop: int) -> List[str]:
        lst = self.lists.get(key, [])
        n = len(lst)

        # 음수 인덱스 대충 처리 (Redis 느낌)
        if start < 0:
            start = max(0, n + start)
        if stop < 0:
            stop = n + stop

        # Redis는 stop 포함, 파이썬은 미포함이라 +1
        return lst[start : stop + 1]

    # ---- String / KV 계열 ----
    async def set(self, key: str, value: str) -> bool:
        self.kv[str(key)] = str(value)
        return True

    async def get(self, key: str) -> Optional[str]:
        return self.kv.get(str(key))

    # ---- 만료 시간(TTL) 흉내 ----
    async def expire(self, key: str, ttl: int) -> bool:
        # 로컬 개발용이라 실제 만료는 구현 안 하고 True만 반환
        # (insight_cache에서 에러 없이 넘어가게 하기 위한 용도)
        return True

    # ---- 삭제 ----
    async def delete(self, key: str) -> int:
        removed = 0
        if key in self.hashes:
            del self.hashes[key]
            removed += 1
        if key in self.lists:
            del self.lists[key]
            removed += 1
        if key in self.kv:
            del self.kv[key]
            removed += 1
        return removed


# 프로젝트 전체에서 import 하는 redis 객체
redis = InMemoryRedis()
logger.warning("Using InMemoryRedis: 실제 Redis 서버 없이 메모리 캐시만 사용합니다.")
