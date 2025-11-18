import os
from dotenv import load_dotenv

load_dotenv()

def _env_bool(key: str, default: bool) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return str(val).strip().lower() not in {"0", "false", "no", "off"}


def _env_int(key: str, default: int) -> int:
    val = os.getenv(key)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


class Settings:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    NEWS_API_KEY = os.getenv("NEWS_API_KEY")
    BASE_NEWS_URL = "https://newsapi.org/v2/top-headlines"
    PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_SSL_VERIFY = _env_bool("REDIS_SSL_VERIFY", True)

    LINK_FETCH_ENABLED = _env_bool("LINK_FETCH_ENABLED", True)
    LINK_MAX_RESPONSE_BYTES = _env_int("LINK_MAX_RESPONSE_BYTES", 1_500_000)
    LINK_REQUEST_TIMEOUT = _env_int("LINK_REQUEST_TIMEOUT", 10)
    LINK_CACHE_TTL_SEC = _env_int("LINK_CACHE_TTL_SEC", 600)
    LINK_PREVIEW_EMIT = _env_bool("LINK_PREVIEW_EMIT", True)
    LINK_AUTO_ANALYZE = _env_bool("LINK_AUTO_ANALYZE", False)
    LINK_TEXT_MAX_CHARS = _env_int("LINK_TEXT_MAX_CHARS", 5000)

settings = Settings()

