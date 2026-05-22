"""
ScraperTool — fetches a URL and extracts visible text and company name via BeautifulSoup.

Returns a dict {"text": str, "company_name": str | None} so the caller can use
structured metadata (schema.org, og:site_name) for company name extraction.
max_chars guard keeps content within LLM context window budget.
"""
import json as _json
import logging
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; HumanMaximizer-LeadBot/1.0; "
        "+https://humanmaximizer.com)"
    )
}
_BLOCKED_EXTENSIONS = {
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg",
    ".zip", ".exe", ".mp4", ".mp3",
}
_BLOCKED_DOMAINS = {
    "linkedin.com", "facebook.com", "twitter.com", "instagram.com",
    "youtube.com", "wikipedia.org", "glassdoor.com", "indeed.com",
    "naukri.com", "ambitionbox.com",
}

_ORG_TYPES = {"Organization", "Corporation", "LocalBusiness", "Company"}


class ScraperTool:
    def __init__(self, timeout: int = 8, max_chars: int = 4000) -> None:
        self.timeout = timeout
        self.max_chars = max_chars

    def _is_scrapeable(self, url: str) -> bool:
        lower = url.lower()
        if not (lower.startswith("http://") or lower.startswith("https://")):
            return False
        if any(lower.endswith(ext) for ext in _BLOCKED_EXTENSIONS):
            return False
        if any(domain in lower for domain in _BLOCKED_DOMAINS):
            return False
        return True

    def _extract_company_name(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract organisation name from structured metadata.

        Priority: schema.org JSON-LD → og:site_name → application-name meta.
        Returns None when nothing trustworthy is found.
        """
        # 1. schema.org JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                raw = script.string or ""
                data = _json.loads(raw)
                if isinstance(data, list):
                    data = data[0] if data else {}
                org_type = data.get("@type", "")
                if org_type in _ORG_TYPES:
                    name = (data.get("name") or "").strip()
                    if 2 <= len(name) <= 120:
                        return name
            except Exception:
                continue

        # 2. og:site_name
        og = soup.find("meta", property="og:site_name")
        if og:
            name = (og.get("content") or "").strip()
            if 2 <= len(name) <= 120:
                return name

        # 3. application-name
        app = soup.find("meta", attrs={"name": "application-name"})
        if app:
            name = (app.get("content") or "").strip()
            if 2 <= len(name) <= 120:
                return name

        return None

    def scrape(self, url: str) -> dict:
        """Fetch URL and return {"text": str, "company_name": str | None}.

        text is capped at max_chars. company_name is extracted from structured
        metadata before navigation elements are stripped.
        """
        if not self._is_scrapeable(url):
            logger.debug("Skipping non-scrapeable URL: %s", url)
            return {"text": "", "company_name": None}

        try:
            with httpx.Client(
                timeout=self.timeout,
                follow_redirects=True,
                headers=_HEADERS,
            ) as client:
                response = client.get(url)
                response.raise_for_status()
                if "text/html" not in response.headers.get("content-type", ""):
                    return {"text": "", "company_name": None}

                soup = BeautifulSoup(response.text, "html.parser")

                # Extract company name before stripping structural tags
                company_name = self._extract_company_name(soup)

                for tag in soup(["script", "style", "nav", "footer", "header", "aside",
                                  "form", "button", "noscript", "iframe", "svg"]):
                    tag.decompose()

                text = soup.get_text(separator="\n", strip=True)
                return {"text": text[: self.max_chars], "company_name": company_name}

        except Exception as exc:
            logger.warning("Scrape failed for %s: %s", url, exc)
            return {"text": "", "company_name": None}
