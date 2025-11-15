from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
import time
from dataclasses import dataclass
from typing import Dict, Optional
from urllib.parse import urlparse, urlunparse, urlencode, urljoin, parse_qsl

import httpx
from bs4 import BeautifulSoup
import tldextract

from app.core.config import settings

try:
    from trafilatura import extract as trafilatura_extract  # type: ignore

    _TRAFILATURA_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    trafilatura_extract = None
    _TRAFILATURA_AVAILABLE = False


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/119.0.0.0 Safari/537.36"
)

TRACKING_PARAM_PREFIXES = ("utm_", "icid", "ga_", "fb_", "mc_")
TRACKING_PARAM_KEYS = {
    "fbclid",
    "gclid",
    "yclid",
    "mc_cid",
    "mc_eid",
    "ref",
}

HTML_MIME_PATTERN = re.compile(r"(text/html|application/xhtml\+xml)", re.IGNORECASE)

PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


@dataclass
class CacheEntry:
    expires_at: float
    payload: Dict[str, Optional[str]]


_cache: Dict[str, CacheEntry] = {}
_cache_lock = asyncio.Lock()
_host_safety_cache: Dict[str, bool] = {}
_host_cache_lock = asyncio.Lock()


def _ensure_scheme(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme:
        return url
    return f"http://{url}"


def normalize_url(url: str) -> str:
    """Strip tracking params and fragments while keeping ordering."""
    if not url:
        return url
    url = url.strip()
    url = _ensure_scheme(url)
    parsed = urlparse(url)
    query_pairs = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=False)
        if not _is_tracking_param(k)
    ]
    cleaned = parsed._replace(
        query=urlencode(query_pairs, doseq=True),
        fragment="",
    )
    return urlunparse(cleaned)


def _is_tracking_param(key: str) -> bool:
    lower = key.lower()
    if lower in TRACKING_PARAM_KEYS:
        return True
    return any(lower.startswith(prefix) for prefix in TRACKING_PARAM_PREFIXES)


async def _is_safe_host(hostname: str) -> bool:
    if not hostname:
        return False
    host_lower = hostname.lower()
    if host_lower == "localhost" or host_lower.endswith(".local"):
        return False

    async with _host_cache_lock:
        cached = _host_safety_cache.get(host_lower)
        if cached is not None:
            return cached

    loop = asyncio.get_running_loop()
    try:
        addrinfo = await loop.run_in_executor(
            None, lambda: socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
        )
    except socket.gaierror:
        safe = False
    else:
        safe = True
        for info in addrinfo:
            ip_str = info[4][0]
            try:
                ip_obj = ipaddress.ip_address(ip_str)
            except ValueError:
                safe = False
                break
            if any(ip_obj in net for net in PRIVATE_NETWORKS):
                safe = False
                break

    async with _host_cache_lock:
        _host_safety_cache[host_lower] = safe

    return safe


async def _assert_safe_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("허용되지 않은 URL 스키마입니다.")
    if not await _is_safe_host(parsed.hostname or ""):
        raise ValueError("허용되지 않은 호스트입니다.")


async def _fetch_html(url: str) -> tuple[str, str]:
    timeout = httpx.Timeout(
        settings.LINK_REQUEST_TIMEOUT, connect=settings.LINK_REQUEST_TIMEOUT
    )
    limits = httpx.Limits(max_connections=5, max_keepalive_connections=2)

    async with httpx.AsyncClient(
        timeout=timeout,
        limits=limits,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
    ) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if not HTML_MIME_PATTERN.search(content_type):
                raise ValueError("HTML 문서가 아닙니다.")

            final_url = str(response.url)
            await _assert_safe_url(final_url)

            total = 0
            chunks: list[bytes] = []
            async for chunk in response.aiter_bytes():
                total += len(chunk)
                if total > settings.LINK_MAX_RESPONSE_BYTES:
                    raise ValueError("응답 본문 크기 제한을 초과했습니다.")
                chunks.append(chunk)

    raw_bytes = b"".join(chunks)
    encoding = response.encoding or getattr(response, "charset_encoding", None) or "utf-8"  # type: ignore[name-defined]
    html = raw_bytes.decode(encoding, errors="ignore")
    return final_url, html


def _extract_meta_with_bs4(html: str, base_url: str) -> Dict[str, Optional[str]]:
    soup = BeautifulSoup(html, "lxml")

    def _get_meta(property_name: str) -> Optional[str]:
        tag = soup.find("meta", property=f"og:{property_name}") or soup.find(
            "meta", attrs={"name": f"og:{property_name}"}
        )
        if tag and tag.get("content"):
            return tag.get("content").strip()
        return None

    title = _get_meta("title")
    if not title:
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

    description = _get_meta("description")
    if not description:
        tag = soup.find("meta", attrs={"name": "description"})
        if tag and tag.get("content"):
            description = tag.get("content").strip()

    image = _get_meta("image")
    if not image:
        twitter_card = soup.find("meta", attrs={"name": "twitter:image"})
        if twitter_card and twitter_card.get("content"):
            image = twitter_card.get("content").strip()
    if image and not image.lower().startswith(("http://", "https://", "data:")):
        image = urljoin(base_url, image)

    site_name = _get_meta("site_name")
    if not site_name:
        tag = soup.find("meta", attrs={"property": "og:site_name"})
        if tag and tag.get("content"):
            site_name = tag.get("content").strip()

    return {
        "title": title,
        "description": description,
        "image": image,
        "site_name": site_name,
    }


def _clean_text(text: str) -> str:
    trimmed = re.sub(r"\s+", " ", text or "").strip()
    if len(trimmed) > settings.LINK_TEXT_MAX_CHARS:
        return trimmed[: settings.LINK_TEXT_MAX_CHARS].rstrip() + "…"
    return trimmed


def _extract_text(html: str) -> str:
    if _TRAFILATURA_AVAILABLE and trafilatura_extract:
        try:
            extracted = trafilatura_extract(
                html,
                include_comments=False,
                include_tables=False,
                favor_precision=True,
            )
            if extracted:
                return _clean_text(extracted)
        except Exception:
            pass

    soup = BeautifulSoup(html, "lxml")
    candidates = []
    for selector in ("article", "main"):
        for node in soup.select(selector):
            text = node.get_text(separator=" ", strip=True)
            candidates.append((len(text), text))

    if not candidates:
        paragraphs = [
            p.get_text(separator=" ", strip=True) for p in soup.find_all("p")
        ]
        paragraphs = [p for p in paragraphs if len(p.split()) > 5]
        text = " ".join(paragraphs)
    else:
        candidates.sort(reverse=True)
        text = candidates[0][1]

    return _clean_text(text)


async def _get_cache(url: str) -> Optional[Dict[str, Optional[str]]]:
    async with _cache_lock:
        entry = _cache.get(url)
        if not entry:
            return None
        if entry.expires_at < time.time():
            del _cache[url]
            return None
        return dict(entry.payload)


async def _set_cache(url: str, payload: Dict[str, Optional[str]]) -> None:
    async with _cache_lock:
        expires = time.time() + max(60, settings.LINK_CACHE_TTL_SEC)
        _cache[url] = CacheEntry(expires_at=expires, payload=dict(payload))


async def fetch_link(url: str) -> Dict[str, Optional[str]]:
    """
    Fetch remote URL, return metadata & text payload with caching.
    """
    if not settings.LINK_FETCH_ENABLED:
        raise RuntimeError("링크 수집 기능이 비활성화되어 있습니다.")

    normalized = normalize_url(url)
    await _assert_safe_url(normalized)

    cached = await _get_cache(normalized)
    if cached:
        return cached

    final_url, html = await _fetch_html(normalized)
    await _assert_safe_url(final_url)

    meta = _extract_meta_with_bs4(html, final_url)
    text = _extract_text(html)

    host = urlparse(final_url).hostname or ""
    if host:
        host = host.lower()

    site_name = meta.get("site_name")
    if not site_name:
        ext = tldextract.extract(final_url)
        if ext.registered_domain:
            site_name = ext.registered_domain.title()
        elif host:
            site_name = host

    payload: Dict[str, Optional[str]] = {
        "url": final_url,
        "host": host,
        "site_name": site_name,
        "title": meta.get("title"),
        "description": meta.get("description"),
        "image": meta.get("image"),
        "text": text or None,
    }

    await _set_cache(final_url, payload)
    if normalized != final_url:
        await _set_cache(normalized, payload)

    return payload

