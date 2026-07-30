from __future__ import annotations

import ipaddress
import json
import logging
import re
from typing import Any
from urllib.parse import urlsplit

import httpx

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)

_TIMEOUT = 30
_MAX_LENGTH = 8000


def _url_allowed(url: str) -> tuple[bool, str]:
    try:
        parsed = urlsplit(url.strip())
    except ValueError:
        return False, "target URL is not allowed"

    if parsed.scheme.lower() not in {"http", "https"}:
        return False, "target URL is not allowed"
    if not parsed.hostname:
        return False, "target URL is not allowed"
    if parsed.username or parsed.password:
        return False, "target URL is not allowed"

    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
        return False, "target URL is not allowed"

    ip_host = host.split("%", 1)[0]
    try:
        ip = ipaddress.ip_address(ip_host)
    except ValueError:
        return True, ""

    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
        or not ip.is_global
    ):
        return False, "target URL is not allowed"
    return True, ""


def _html_to_text(html: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.S | re.I)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_title(html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    if match:
        return match.group(1).strip()
    return ""


def read_url(url: str, no_cache: bool = False) -> dict:
    target_url = url.strip()
    allowed, error = _url_allowed(target_url)
    if not allowed:
        return {"status": "error", "error": error}

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FoodTrack/1.0",
            "Accept": "text/html,application/xhtml+xml,text/plain",
        }
        if no_cache:
            headers["Cache-Control"] = "no-cache"

        resp = httpx.get(target_url, headers=headers, timeout=_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "")
        raw = resp.text

        title = _extract_title(raw)

        if "text/html" in content_type:
            text = _html_to_text(raw)
        else:
            text = raw

        if len(text) > _MAX_LENGTH:
            text = text[:_MAX_LENGTH] + f"\n\n... (truncated, total {len(raw)} chars)"

        return {
            "status": "ok",
            "title": title,
            "url": target_url,
            "content": text,
            "length": len(raw),
        }

    except httpx.HTTPStatusError as e:
        return {"status": "error", "error": f"HTTP {e.response.status_code}: {e.response.reason_phrase}"}
    except httpx.TimeoutException:
        return {"status": "error", "error": "Request timed out"}
    except httpx.RequestError as e:
        return {"status": "error", "error": f"Connection failed: {e}"}
    except Exception as exc:
        logger.warning("read_url request failed: %s", exc)
        return {"status": "error", "error": f"Request failed: {exc}"}


class WebReaderTool(BaseTool):
    name = "read_url"
    description = (
        "Fetch web page content: provide a URL and receive the page as text. "
        "Useful for reading articles, documentation, product pages, etc."
    )
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL of the web page to read"},
            "no_cache": {"type": "boolean", "description": "Request a fresh fetch", "default": False},
        },
        "required": ["url"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        result = read_url(kwargs["url"], no_cache=bool(kwargs.get("no_cache", False)))
        return json.dumps(result, ensure_ascii=False)
