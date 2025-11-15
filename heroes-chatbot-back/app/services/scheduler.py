import asyncio
from datetime import datetime, time as dtime
import zoneinfo
from .ingestion import run_daily_ingestion

TZ = zoneinfo.ZoneInfo("Asia/Seoul")

async def scheduler_loop():
    while True:
        now = datetime.now(TZ)
        target = datetime.combine(now.date(), dtime(17,30), TZ)  # 장마감+30분
        if now >= target:
            target = datetime.combine((now + timedelta(days=1)).date(), dtime(17,30), TZ)
        await asyncio.sleep((target - now).total_seconds())
        try:
            await run_daily_ingestion()
        except Exception as e:
            from app.utils.logger import logger
            logger.warning(f"[ingestion] failed: {e}")
