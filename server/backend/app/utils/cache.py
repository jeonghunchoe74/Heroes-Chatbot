from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from app.utils.logger import logger


class Cache:
    """
    메모리 캐싱 유틸리티 (간단한 구현)
    """
    
    def __init__(self, default_ttl: int = 3600):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        캐시에 값 저장
        """
        ttl = ttl or self.default_ttl
        expires_at = datetime.now() + timedelta(seconds=ttl)
        
        self.cache[key] = {
            "value": value,
            "expires_at": expires_at
        }
        
        logger.debug(f"캐시 저장: {key} (TTL: {ttl}초)")
    
    def get(self, key: str) -> Optional[Any]:
        """
        캐시에서 값 조회
        """
        if key not in self.cache:
            return None
        
        item = self.cache[key]
        expires_at = item["expires_at"]
        
        if datetime.now() > expires_at:
            # 만료된 항목 삭제
            del self.cache[key]
            logger.debug(f"캐시 만료: {key}")
            return None
        
        logger.debug(f"캐시 조회: {key}")
        return item["value"]
    
    def delete(self, key: str) -> None:
        """
        캐시에서 항목 삭제
        """
        if key in self.cache:
            del self.cache[key]
            logger.debug(f"캐시 삭제: {key}")
    
    def clear(self) -> None:
        """
        캐시 전체 삭제
        """
        self.cache.clear()
        logger.info("캐시 전체 삭제")
    
    def cleanup_expired(self) -> None:
        """
        만료된 항목 정리
        """
        now = datetime.now()
        expired_keys = [
            key for key, item in self.cache.items()
            if now > item["expires_at"]
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.debug(f"만료된 캐시 항목 {len(expired_keys)}개 정리")


cache = Cache()

