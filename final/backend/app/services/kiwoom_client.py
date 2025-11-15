import asyncio
import httpx
import os
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class KiwoomClient:
    """
    Kiwoom REST 래퍼(비동기)
    - ka10001: /api/dostk/stkinfo (주식 기본/시세 정보)
    - headers: Bearer 토큰, api-id, cont-yn/next-key(페이지)
    환경변수:
    - KIWOOM_BASE_URL     (기본: https://api.kiwoom.com)
    - KIWOOM_ACCESS_TOKEN (Bearer 토큰)
    """

    def __init__(self,
                base_url: str | None = None,
                token: str | None = None,
                timeout: int = 10,
                rate_limit: int = 5):
        self.base_url = (base_url or os.getenv("KIWOOM_BASE_URL") or "https://api.kiwoom.com").rstrip("/")
        self.token = token or os.getenv("KIWOOM_ACCESS_TOKEN") or ""
        self.timeout = timeout
        self.sem = asyncio.Semaphore(rate_limit)
        self._client = httpx.AsyncClient(timeout=self.timeout)

        # 토큰 프리픽스 로깅(디버깅용)
        logger.info("[KIWOOM] base_url=%s token_prefix=%s", self.base_url, (self.token[:10] if self.token else ""))

        if not self.token:
            logger.warning("[KIWOOM] KIWOOM_ACCESS_TOKEN not set (live calls will fail)")

    async def close(self):
        await self._client.aclose()

    async def _post_json(self, endpoint: str, data: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        async with self.sem:
            r = await self._client.post(self.base_url + endpoint, json=data, headers=headers)
            r.raise_for_status()
            return r.json()

    async def ka10001_once(self, stk_cd: str,
                        cont_yn: str = "N",
                        next_key: str = "") -> Dict[str, Any]:
        """
        ka10001 1회 호출(단건)
        """
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": f"Bearer {self.token}",
            "api-id": "ka10001",
            "cont-yn": cont_yn,
            "next-key": next_key,
        }
        payload = {"stk_cd": stk_cd}
        return await self._post_json("/api/dostk/stkinfo", payload, headers)

    async def ka10001(self, stk_cd: str) -> Dict[str, Any]:
        """
        ka10001 전체 페이지 수집(필요 시 확장).
        현재는 단건 응답을 그대로 반환.
        """
        return await self.ka10001_once(stk_cd)

    async def ka10001_batch(self, codes: List[str]) -> List[Dict[str, Any]]:
        """
        여러 종목 일괄 조회 → list[dict] 반환
        """
        out: List[Dict[str, Any]] = []
        for code in codes:
            try:
                r = await self.ka10001(code)
                body = r if isinstance(r, dict) else {}
                body["_stk_cd"] = code  # 원문에 종목코드 키 없을 때 추적용
                out.append(body)
            except Exception as e:
                out.append({"_stk_cd": code, "_error": str(e)})
        return out
