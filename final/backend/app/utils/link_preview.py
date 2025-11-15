import re
from typing import Dict, List, Optional

from app.services.link_service import fetch_link, normalize_url

URL_REGEX = re.compile(
    r'((?:https?://|www\d{0,3}[.]|[a-z0-9.-]+\.[a-z]{2,})(?:[^\s<>()"]*)?)',
    re.IGNORECASE,
)


def extract_urls(text: str) -> List[str]:
    if not text:
        return []
    urls: List[str] = []
    seen: set[str] = set()
    for match in URL_REGEX.finditer(text):
        url = match.group(1)
        if not url or url in seen:
            continue
        seen.add(url)
        urls.append(url)
    return urls


def normalize(url: str) -> str:
    return normalize_url(url or "")


async def fetch_og(url: str) -> Dict[str, Optional[str]]:
    meta = await fetch_link(url)
    if not meta:
        return {}

    resolved_url = meta.get("url") or normalize(url)
    title = meta.get("title") or meta.get("site_name") or resolved_url
    host = meta.get("host")
    if not host and resolved_url:
        parsed = re.match(r"https?://([^/]+)", resolved_url)
        host = parsed.group(1) if parsed else None

    preview: Dict[str, Optional[str]] = {
        "url": resolved_url,
        "title": title,
        "description": meta.get("description"),
        "image": meta.get("image"),
        "site_name": meta.get("site_name"),
        "host": host,
    }

    if meta.get("text"):
        preview["text"] = meta["text"]

    return preview

