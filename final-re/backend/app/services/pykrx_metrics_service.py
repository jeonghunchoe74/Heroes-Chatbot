from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


async def compute_peg_ratio(symbol: str, per_value: Optional[float] = None) -> Tuple[Optional[float], Optional[float]]:
    """
    Calculates PEG ratio and EPS 성장률(%) for the given Korean stock code using pykrx fundamentals.
    Returns (peg, eps_growth_percent). Any failure yields (None, None).
    """

    def _run() -> Tuple[Optional[float], Optional[float]]:
        try:
            from pykrx import stock
        except Exception as exc:
            logger.error("pykrx import failed: %s", exc, exc_info=True)
            return None, None

        try:
            end = datetime.now()
            start = end - timedelta(days=550)
            df = stock.get_market_fundamental_by_date(
                start.strftime("%Y%m%d"),
                end.strftime("%Y%m%d"),
                symbol,
            )
        except Exception as exc:
            logger.error("pykrx fundamental fetch failed for %s: %s", symbol, exc, exc_info=True)
            return None, None

        if df is None or df.empty:
            return None, None

        df = df.dropna(subset=["EPS"]).sort_index()
        if df.empty:
            return None, None

        latest_row = df.iloc[-1]
        latest_eps = float(latest_row.get("EPS") or 0)
        if latest_eps == 0:
            return None, None

        latest_date = latest_row.name.to_pydatetime() if hasattr(latest_row.name, "to_pydatetime") else latest_row.name
        if not isinstance(latest_date, datetime):
            latest_date = datetime.now()

        target_date = latest_date - timedelta(days=365)
        earlier_rows = df[df.index <= pd.Timestamp(target_date)]
        if earlier_rows.empty:
            earlier_rows = df.iloc[:-1]
        if earlier_rows.empty:
            return None, None

        prev_eps = float(earlier_rows.iloc[-1].get("EPS") or 0)
        if prev_eps == 0:
            return None, None

        eps_growth_ratio = (latest_eps - prev_eps) / abs(prev_eps)
        if eps_growth_ratio <= 0:
            return None, None

        eps_growth_percent = eps_growth_ratio * 100
        per_for_calc = per_value
        if per_for_calc is None:
            per_candidate = latest_row.get("PER")
            per_for_calc = float(per_candidate) if per_candidate not in (None, "") else None

        if per_for_calc in (None, 0):
            return None, eps_growth_percent

        peg = per_for_calc / eps_growth_percent if eps_growth_percent else None
        return peg, eps_growth_percent

    return await asyncio.to_thread(_run)

