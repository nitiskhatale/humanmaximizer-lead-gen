"""
ResearchAgent node — populates company data fields in LeadState.

Calls SerpAPI to search, scrapes the top result URL, then calls
Mistral-7B to generate raw_summary from the enriched data.
"""
import logging
import re
import time

from langchain_ollama import OllamaLLM
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from models.state import LeadState
from observability.metrics import llm_calls
from prompts import load_prompt
from tools.contact_finder import ContactFinderTool
from tools.scraper import ScraperTool
from tools.serp_search import SerpSearchTool

logger = logging.getLogger(__name__)

_llm = OllamaLLM(
    model=settings.ollama_model,
    base_url=settings.ollama_base_url,
    temperature=0.2,
    num_ctx=8192,
    repeat_penalty=1.1,
    num_gpu=settings.ollama_num_gpu,
)

_scraper = ScraperTool()
_contact_finder = ContactFinderTool()


def research_node(state: LeadState) -> LeadState:
    """LangGraph node: research and enrich the lead."""
    t0 = time.time()
    logger.info("[ResearchAgent] keyword='%s' location='%s'", state["keyword"], state["location"])

    try:
        enriched = _run_live(state)

        enriched["raw_summary"] = _generate_summary(enriched)
        enriched["processing_time_ms"] = int((time.time() - t0) * 1000)
        logger.info(
            "[ResearchAgent] done: company='%s' industry='%s' employees=%s",
            enriched["company_name"],
            enriched["industry"],
            enriched["employee_count"],
        )
        return {**state, **enriched}

    except Exception as exc:
        logger.error("[ResearchAgent] failed: %s", exc, exc_info=True)
        errors = list(state.get("errors", []))
        errors.append(f"ResearchAgent: {exc}")
        return {**state, "errors": errors, "status": "error"}


def _is_directory_url(url: str) -> bool:
    """Return True if the URL belongs to a job board, aggregator, or news site."""
    lower = url.lower()
    return any(kw in lower for kw in _DIRECTORY_URL_KEYWORDS)


def _run_live(state: LeadState) -> dict:
    """Search, scrape the first usable result, extract company data."""
    serp = SerpSearchTool()
    results = serp.run(state["keyword"], state["location"])
    if not results:
        raise RuntimeError("Search returned no results")

    candidates = _extract_candidates(results, max_companies=1, base_errors=list(state.get("errors", [])))
    if not candidates:
        raise RuntimeError("No usable result found from search results")
    return candidates[0]


def research_all_candidates(
    keyword: str,
    location: str,
    max_companies: int = 5,
) -> list[dict]:
    """
    Search for multiple companies and return enriched data for each.

    Searches once, scrapes each non-directory result, deduplicates by domain,
    and returns up to max_companies enriched dicts ready for qualification.
    LLM summaries are NOT generated here — call generate_summary(data) per company.
    """
    serp = SerpSearchTool()
    results = serp.run(keyword, location, num_results=max(max_companies * 2, 10))
    if not results:
        raise RuntimeError("Search returned no results")
    candidates = _extract_candidates(results, max_companies=max_companies)
    if not candidates:
        raise RuntimeError("No usable companies found for this keyword and location")
    return candidates


def _extract_candidates(
    results: list[dict],
    max_companies: int,
    base_errors: list | None = None,
) -> list[dict]:
    """Shared extraction loop used by both single-company and multi-company paths."""
    candidates: list[dict] = []
    seen_domains: set[str] = set()
    errors = base_errors or []

    for result in results:
        if len(candidates) >= max_companies:
            break

        url = result.get("link", "")
        if _is_directory_url(url):
            logger.debug("[ResearchAgent] skipping directory URL: %s", url)
            continue

        domain = _extract_domain(url)
        if not domain or domain in seen_domains:
            continue

        snippet = result.get("snippet", "")
        title = result.get("title", "")

        scraped = _scraper.scrape(url)
        if isinstance(scraped, dict):
            scraped_text = scraped.get("text", "")
            meta_company_name = scraped.get("company_name")
        else:
            scraped_text = scraped or ""
            meta_company_name = None

        if not scraped_text and not snippet:
            continue

        text = scraped_text or snippet
        seen_domains.add(domain)

        decision_makers = _contact_finder.find(text, domain=domain)
        candidates.append({
            "company_name": meta_company_name or _clean_company_name(title, url),
            "domain": domain,
            "description": _extract_clean_description(scraped_text, snippet),
            "employee_count": _extract_employee_count(text),
            "industry": _guess_industry(text),
            "hq_location": _extract_location(text),
            "tech_stack": [],
            "decision_makers": decision_makers,
            "growth_signal": "unknown",
            "status": "pending",
            "errors": list(errors),
        })
        logger.info(
            "[ResearchAgent] candidate[%d]: %s (%s)",
            len(candidates), candidates[-1]["company_name"], domain,
        )

    return candidates


def generate_summary(data: dict) -> str:
    """Public wrapper — generate an LLM summary for a pre-extracted company dict."""
    return _generate_summary(data)


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=False)
def _invoke_llm(prompt: str) -> str:
    llm_calls.labels(agent="research").inc()
    return _llm.invoke(prompt).strip()


def _generate_summary(data: dict) -> str:
    """Call Mistral to produce the raw_summary paragraph (2 retries on transient failure)."""
    prompt = load_prompt(
        "research_summary.j2",
        company_name=data.get("company_name", ""),
        domain=data.get("domain", ""),
        industry=data.get("industry", ""),
        employee_count=data.get("employee_count"),
        hq_location=data.get("hq_location", ""),
        tech_stack=data.get("tech_stack", []),
        description=data.get("description", ""),
    )
    try:
        return _invoke_llm(prompt)
    except Exception as exc:
        logger.warning("[ResearchAgent] LLM summary failed after retries: %s", exc)
        company = data.get("company_name") or "This company"
        industry = data.get("industry") or "unknown"
        summary = f"{company} operates in the {industry} sector"
        if data.get("employee_count"):
            summary += f" with approximately {data['employee_count']} employees"
        if data.get("hq_location"):
            summary += f", headquartered in {data['hq_location']}"
        return summary + "."


def _extract_domain(url: str) -> str:
    from urllib.parse import urlparse
    return urlparse(url).netloc.lstrip("www.")


def _guess_industry(text: str) -> str:
    text_lower = text.lower()
    if any(w in text_lower for w in ["hrms", "hris", "payroll software", "hr software", "workforce management"]):
        return "HR Technology"
    if any(w in text_lower for w in ["manufacturing", "factory", "plant", "forging", "fabrication"]):
        return "Manufacturing"
    if any(w in text_lower for w in ["hospital", "healthcare", "clinic", "diagnostic", "pharmaceutical"]):
        return "Healthcare"
    if any(w in text_lower for w in ["bank", "finance", "insurance", "nbfc", "lending"]):
        return "BFSI"
    if any(w in text_lower for w in ["retail", "ecommerce", "e-commerce", "store", "consumer goods"]):
        return "Retail"
    if any(w in text_lower for w in ["it services", "bpo", "outsourcing", "software services", "saas"]):
        return "IT Services"
    return "Unknown"


_ARTICLE_PREFIXES = re.compile(
    r"^(best\b|top\s+\d+|compare\b|review\b|guide\b|how\s+to\b|what\s+is\b|list\s+of\b|\d+\s+best\b)",
    re.IGNORECASE,
)

_NOISE_PHRASES = re.compile(
    r"(contact\s+us|get\s+started|book\s+a\s+demo|sign\s+up|subscribe|call\s+us|"
    r"click\s+here|learn\s+more|request\s+a\s+|free\s+trial|read\s+more|"
    r"©|\bfaq\b|cookie|privacy\s+policy|terms\s+of|all\s+rights\s+reserved|"
    r"testimonial|trusted\s+by|our\s+clients|schedule\s+a\s+call|"
    r"#\d+\s|\b\d+\s+best\b|\btop\s+\d+\b)",
    re.IGNORECASE,
)
_SKIP_DOMAIN_PARTS = {"www", "app", "api", "blog", "explore", "help", "support", "co", "org", "net"}

# Keywords whose presence anywhere in the URL indicates an aggregator/directory page,
# not the actual company website. Used to skip results in live mode.
_DIRECTORY_URL_KEYWORDS = {
    "glassdoor", "naukri", "ambitionbox", "justdial", "indiamart",
    "builtin", "tracxn", "crunchbase", "zaubacorp", "tofler", "comparably",
    "dnb.com", "mca.gov.in", "opencorporates", "bloomberg.com",
    "reuters.com", "economictimes", "moneycontrol", "livemint",
    "thehindu.com", "businessstandard", "yourstory.com", "inc42.com",
}

_EMPLOYEE_PATTERNS = [
    re.compile(r"(\d[\d,]+)\s*\+?\s*(?:employees|people|staff|workforce|team\s+members)", re.IGNORECASE),
    re.compile(r"(?:employing|employs|over|more\s+than|around|approximately)\s+(\d[\d,]+)\s*(?:employees|people|staff)", re.IGNORECASE),
    re.compile(r"workforce\s+of\s+(?:over\s+)?(\d[\d,]+)", re.IGNORECASE),
]

_LOCATION_PATTERNS = [
    re.compile(r"headquartered\s+in\s+([A-Z][a-zA-Z\s]+,\s*[A-Z][a-zA-Z\s]+?)(?:\.|,|\n)", re.MULTILINE),
    re.compile(r"head\s*quarters?\s+(?:in|at)\s+([A-Z][a-zA-Z\s]+,\s*[A-Z][a-zA-Z\s]+?)(?:\.|,|\n)", re.IGNORECASE | re.MULTILINE),
    re.compile(r"based\s+in\s+([A-Z][a-zA-Z\s]+,\s*[A-Z][a-zA-Z\s]+?)(?:\.|,|\n)", re.MULTILINE),
]


def _clean_company_name(title: str, url: str) -> str:
    """Strip marketing text from page title; fall back to domain-derived name."""
    for sep in (" | ", " — ", " – ", " - ", " : "):
        if sep in title:
            parts = [p.strip() for p in title.split(sep)]
            candidates = [
                p for p in parts
                if 2 <= len(p) <= 60 and not _ARTICLE_PREFIXES.match(p)
            ]
            if candidates:
                return min(candidates, key=len)
    from urllib.parse import urlparse
    parts = urlparse(url).netloc.split(".")
    for part in reversed(parts[:-1]):
        if part.lower() not in _SKIP_DOMAIN_PARTS and len(part) > 2:
            return part.replace("-", " ").title()
    return parts[0].replace("-", " ").title() if parts else title[:60].strip()


def _extract_clean_description(scraped_text: str, snippet: str) -> str:
    """Return 2-3 factual sentences, filtered for noise, from snippet then scraped text."""
    source = snippet if (snippet and len(snippet) >= 60) else scraped_text
    if not source:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", source)
    factual = [
        s.strip() for s in sentences
        if 40 <= len(s.strip()) <= 300
        and not _NOISE_PHRASES.search(s)
        and s.count(" . ") < 3
    ]
    return " ".join(factual[:3])[:500]


def _extract_employee_count(text: str) -> int | None:
    """Regex extraction of employee headcount. Returns None when confidence is low."""
    for pat in _EMPLOYEE_PATTERNS:
        m = pat.search(text)
        if m:
            try:
                val = int(m.group(1).replace(",", ""))
                if 10 <= val <= 500_000:
                    return val
            except ValueError:
                pass
    return None


def _extract_location(text: str) -> str:
    """Extract HQ city/country from trusted phrases only."""
    for pat in _LOCATION_PATTERNS:
        m = pat.search(text)
        if m:
            loc = m.group(1).strip().rstrip(".,")
            if 3 <= len(loc) <= 60:
                return loc
    return ""