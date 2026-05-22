"""
SerpSearchTool — calls SerpAPI to return organic Google search results.
Falls back to DuckDuckGo (no key required) when SERPAPI_KEY is not set.
"""
import logging
from typing import Any

import httpx

from config import settings

logger = logging.getLogger(__name__)

_SERPAPI_URL = "https://serpapi.com/search"


class SerpSearchTool:
    def run(self, keyword: str, location: str = "", num_results: int = 10) -> list[dict[str, Any]]:
        """
        Run a web search and return organic results.

        Tries SerpAPI (Google) when SERPAPI_KEY is set; falls back to
        DuckDuckGo (free, no key) otherwise. Returns list of dicts with
        keys: title, link, snippet.
        """
        if settings.serpapi_key:
            return self._serpapi_search(keyword, location, num_results)
        logger.warning(
            "SERPAPI_KEY not set — falling back to DuckDuckGo. "
            "Results may be less precise than SerpAPI Google results."
        )
        return self._duckduckgo_search(keyword, location, num_results)

    def _serpapi_search(self, keyword: str, location: str, num_results: int) -> list[dict[str, Any]]:
        query = f"{keyword} {location}".strip()
        params = {
            "q": query,
            "api_key": settings.serpapi_key,
            "num": num_results,
            "engine": "google",
            "gl": "in",
            "hl": "en",
        }
        try:
            response = httpx.get(_SERPAPI_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data.get("organic_results", [])
        except Exception as exc:
            logger.error("SerpAPI call failed: %s", exc)
            raise RuntimeError(f"SerpAPI error: {exc}") from exc

    def _duckduckgo_search(self, keyword: str, location: str, num_results: int) -> list[dict[str, Any]]:
        """DuckDuckGo fallback — no API key required."""
        try:
            from duckduckgo_search import DDGS
        except ImportError as exc:
            raise RuntimeError(
                "duckduckgo-search package not installed. Run: pip install duckduckgo-search"
            ) from exc

        query = f"{keyword} {location}".strip()
        results: list[dict[str, Any]] = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=num_results, region="in-en"):
                    results.append({
                        "title": r.get("title", ""),
                        "link": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    })
            logger.info("DuckDuckGo returned %d results for query: %s", len(results), query)
            return results
        except Exception as exc:
            logger.error("DuckDuckGo search failed: %s", exc)
            raise RuntimeError(f"DuckDuckGo search error: {exc}") from exc
