from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, List, Dict, Optional
from urllib.parse import urlencode

import httpx

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)

_DEFAULT_BACKENDS = "duckduckgo, google, bing, brave"
_MAX_ATTEMPTS = 3
_BACKOFF_BASE_SECONDS = 0.8


def _bing_search(query: str, max_results: int = 5) -> List[Dict]:
    url = "https://www.bing.com/search?" + urlencode({"q": query})
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        resp = httpx.get(url, headers=headers, timeout=10, follow_redirects=True)
        html = resp.text
    except Exception:
        return []

    blocks = re.findall(r'<li class="b_algo"[^>]*>(.*?)</li>', html, re.S)
    out: List[Dict] = []
    for b in blocks[:max_results]:
        h2 = re.search(r"<h2[^>]*>(.*?)</h2>", b, re.S)
        if not h2:
            continue
        a = re.search(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', h2.group(1), re.S)
        if not a:
            continue
        title = re.sub(r"<[^>]+>", "", a.group(2)).strip()
        href = a.group(1)
        snip_m = re.search(r"<p[^>]*>(.*?)</p>", b, re.S)
        snippet = re.sub(r"<[^>]+>", "", snip_m.group(1)).strip() if snip_m else ""
        if title and href.startswith("http"):
            out.append({"title": title, "href": href, "body": snippet[:180]})
    return out


def web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    max_results = min(max_results, 10)

    try:
        try:
            from ddgs import DDGS
            supports_backend = True
        except ImportError:
            from duckduckgo_search import DDGS
            supports_backend = False

        last_error: Optional[Exception] = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                with DDGS() as client:
                    if supports_backend:
                        raw = list(client.text(query, max_results=max_results, backend=_DEFAULT_BACKENDS))
                    else:
                        raw = list(client.text(query, max_results=max_results))
            except TypeError:
                supports_backend = False
                continue
            except Exception as exc:
                last_error = exc
                if "no results" in str(exc).lower():
                    return {
                        "status": "ok",
                        "query": query,
                        "backends": "duckduckgo",
                        "results": [],
                        "note": "No results found.",
                    }
                logger.warning("web_search attempt %d/%d failed: %s", attempt, _MAX_ATTEMPTS, exc)
                err_msg = str(exc).lower()
                if any(s in err_msg for s in ("timeout", "timed out", "unreachable", "connection")):
                    break
                if attempt < _MAX_ATTEMPTS:
                    time.sleep(_BACKOFF_BASE_SECONDS * attempt)
                continue

            results = [
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                }
                for r in raw
            ]
            return {
                "status": "ok",
                "query": query,
                "backends": _DEFAULT_BACKENDS if supports_backend else "duckduckgo",
                "results": results,
            }

    except ImportError:
        logger.warning("ddgs/duckduckgo_search not installed, falling back to Bing scrape")

    try:
        raw = _bing_search(query, max_results=max_results)
        if raw:
            return {
                "status": "ok",
                "query": query,
                "backends": "bing_fallback",
                "results": [
                    {"title": r["title"], "url": r["href"], "snippet": r["body"]}
                    for r in raw
                ],
            }
    except Exception as exc:
        logger.warning("Bing fallback failed: %s", exc)

    return {
        "status": "error",
        "error": f"Web search failed after {_MAX_ATTEMPTS} attempts: {last_error}",
    }


class WebSearchTool(BaseTool):
    name = "web_search"
    description = (
        "Search the web across free engines (DuckDuckGo, Google, Bing, Brave). "
        "Returns top results with title, URL, and snippet."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results (default 5, max 10)",
                "default": 5,
            },
        },
        "required": ["query"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        query = kwargs["query"]
        max_results = int(kwargs.get("max_results", 5))
        result = web_search(query, max_results)
        return json.dumps(result, ensure_ascii=False)
