# app/services/chatbot_service.py
"""
챗봇 서비스 - LangGraph 기반 오케스트레이션을 사용하는 진입점

레거시 로직은 제거되었고, 모든 요청은 unified_chatbot_service를 통해 처리됩니다.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# --- 레거시 함수들 (다른 모듈에서 사용 중) ---

def _normalise_live_snapshot(raw: Dict, symbol: str) -> Optional[Dict]:
    """
    Kiwoom API 응답을 정규화된 스냅샷으로 변환.
    
    orchestration_graph에서 사용 중이므로 유지.
    """
    if not isinstance(raw, dict):
        logger.warning("live snapshot was not a dict: %s", type(raw))
        return None
    if raw.get("return_code") not in (0, "0", None):
        logger.warning("live snapshot error: %s %s", raw.get("return_code"), raw.get("return_msg"))
        return None

    def _to_float(value: object) -> Optional[float]:
        try:
            return float(str(value).replace(",", ""))
        except Exception:
            return None

    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    current_price_raw = _to_float(raw.get("cur_prc"))
    current_price = None
    if current_price_raw is not None:
        current_price = abs(current_price_raw)
    volume = _to_float(raw.get("trde_qty"))
    trade_value = (current_price * volume) if (current_price is not None and volume is not None) else None

    metric_order = [
        ("per", "PER"),
        ("pbr", "PBR"),
        ("eps", "EPS"),
        ("bps", "BPS"),
        ("dvd_yld", "DIV_YIELD"),
        ("mac", "MKT_CAP"),
        ("oyr_hgst", "52W_H"),
        ("oyr_lwst", "52W_L"),
        ("flu_rt", "CHG_RT"),
    ]

    def _text_snippet() -> str:
        parts = []
        for raw_key, label in metric_order:
            value = raw.get(raw_key)
            if value in (None, "", "-"):
                continue
            parts.append(f"{label} {value}")
        if current_price is not None:
            if isinstance(current_price, (int, float)):
                parts.insert(0, f"현재가 {int(current_price):,}")
            else:
                parts.insert(0, f"현재가 {current_price}")
        if not parts:
            return f"{symbol} 실시간 스냅샷"
        return f"{symbol} 실시간 스냅샷: " + ", ".join(parts)

    # 52주 최저가 음수 처리 (절댓값 사용)
    oyr_lwst_raw = raw.get("oyr_lwst")
    oyr_lwst_value = _to_float(oyr_lwst_raw)
    if oyr_lwst_value is not None and oyr_lwst_value < 0:
        oyr_lwst_value = abs(oyr_lwst_value)
        logger.warning("52주 최저가가 음수였습니다. 절댓값으로 변환: %s -> %s", oyr_lwst_raw, oyr_lwst_value)
    
    record = {
        "section": "market_update",
        "intent": ["news_analysis"],
        "audience": [""],
        "updated": raw.get("trd_dd") or today,
        "symbols": [symbol],
        "text": _text_snippet(),
        "metadata": {
            "source": "kiwoom/rest(live)",
            "api_id": "ka10001",
            "name": (raw.get("stk_nm") or "").strip(),
            "metrics": {
                "PER": _to_float(raw.get("per")),
                "PBR": _to_float(raw.get("pbr")),
                "BPS": _to_float(raw.get("bps")),
                "EPS": _to_float(raw.get("eps")),
                "DIV_YIELD": _to_float(raw.get("dvd_yld") or raw.get("div_yield")),
                "MKT_CAP": _to_float(raw.get("mac")),
                "ROE": _to_float(raw.get("roe")),
                "52W_H": _to_float(raw.get("oyr_hgst")),
                "52W_L": oyr_lwst_value,
                "CHG_RT": _to_float(raw.get("flu_rt")),
                "VOL": volume,
                "TRADE_VALUE": trade_value,
                "CUR": current_price,
            },
        },
    }

    try:
        date_str = str(record["updated"]).replace(".", "").replace("-", "")
        if len(date_str) == 8:
            from datetime import datetime
            record["updated"] = datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d")
        else:
            record["updated"] = str(record["updated"])[:10]
    except Exception:
        record["updated"] = today

    return record


# --- 세션 관리 (레거시 호환) ---

import uuid
from typing import Tuple

# 간단한 인메모리 세션 스토어
_session_store: Dict[str, Dict] = {}


def get_or_create_session(session_id: Optional[str] = None, guru_id: str = "buffett") -> Tuple[str, Dict]:
    """
    세션을 가져오거나 새로 생성.
    
    레거시 API 호환성을 위해 유지.
    """
    if session_id and session_id in _session_store:
        return session_id, _session_store[session_id]
    
    # 새 세션 생성
    new_session_id = session_id or str(uuid.uuid4())
    _session_store[new_session_id] = {
        "guru_id": guru_id,
        "messages": [],
    }
    return new_session_id, _session_store[new_session_id]


def reset_session(session_id: Optional[str] = None) -> str:
    """
    세션을 리셋.
    
    레거시 API 호환성을 위해 유지.
    """
    if session_id and session_id in _session_store:
        _session_store[session_id] = {
            "guru_id": _session_store[session_id].get("guru_id", "buffett"),
            "messages": [],
        }
        return session_id
    
    # 새 세션 생성
    new_session_id = str(uuid.uuid4())
    _session_store[new_session_id] = {
        "guru_id": "buffett",
        "messages": [],
    }
    return new_session_id


# --- API 진입점 ---

async def get_initial_message(guru_id: str) -> Dict[str, object]:
    """
    초기 메시지 및 뉴스 목록 반환.
    
    레거시 API 호환성을 위해 유지.
    """
    try:
        from app.services.news_service import summarize_news
        from app.utils.mentor_utils import normalize_mentor_id
        
        canonical_guru = normalize_mentor_id(guru_id)
        
        # 간단한 인사 메시지
        if canonical_guru == "buffett":
            intro_text = "나는 오래 검증된 원칙을 따릅니다. 복잡함보다 단순함, 단기 이익보다 꾸준함을 중시합니다."
        elif canonical_guru == "lynch":
            intro_text = "일상생활에서 위대한 기업을 찾아내는 '생활 속 투자'를 강조합니다."
        elif canonical_guru == "wood":
            intro_text = "파괴적 혁신 기술에 집중 투자하며, 미래를 바꿀 기술과 기업을 선별합니다."
        else:
            intro_text = "안녕하세요, 저는 투자 멘토입니다."
        
        # 뉴스 가져오기
        try:
            news_items = await summarize_news(canonical_guru)
            if not isinstance(news_items, list):
                news_items = []
        except Exception as exc:
            logger.error("initial news fetch failed: %s", exc, exc_info=True)
            news_items = []
        
        return {"intro": intro_text, "news": news_items}
    except Exception as exc:
        logger.error(f"get_initial_message failed: {exc}", exc_info=True)
        return {"intro": "안녕하세요, 저는 투자 멘토입니다.", "news": []}


async def generate_response(
    user_input: str,
    session_id: Optional[str] = None,
    guru_id: str = "buffett",
    user_type: str = "auto",
    use_unified: bool = True,
) -> Tuple[str, str]:
    """
    Main entry point used by the API layer.
    
    LangGraph 기반 오케스트레이션을 사용합니다.
    
    Args:
        user_input: 사용자 입력 메시지
        session_id: 세션 ID
        guru_id: 멘토 ID
        user_type: 사용자 타입 (현재는 사용하지 않음)
        use_unified: True면 LangGraph 기반 unified_chatbot_service 사용 (기본값: True)
    """
    # LangGraph 기반 통합 서비스 사용
    use_unified_flag = use_unified or os.getenv("USE_UNIFIED_CHATBOT", "true").lower() in {"1", "true", "yes"}
    
    if use_unified_flag:
        try:
            from app.services.unified_chatbot_service import generate_response_unified
            return await generate_response_unified(user_input, guru_id, session_id)
        except ImportError as exc:
            logger.error(f"Failed to import unified chatbot service: {exc}", exc_info=True)
            raise
        except Exception as exc:
            logger.error(f"Unified chatbot service failed: {exc}", exc_info=True)
            raise
    
    # 레거시 로직은 제거됨
    raise NotImplementedError("Legacy chatbot service has been removed. Use unified_chatbot_service.")
