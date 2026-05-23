"""
QualificationAgent node — scores each lead 0–100 across 5 HRMS-fit dimensions.

Scoring is deterministic (rule engine). The LLM is called only to produce
the 2-sentence qualification_reasoning commentary.

Conditional edge: is_qualified = True if score >= 35.
"""
import logging

from langchain_ollama import OllamaLLM
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from models.state import LeadState, ScoreBreakdown
from observability.metrics import llm_calls
from prompts import load_prompt

logger = logging.getLogger(__name__)

_QUALIFICATION_THRESHOLD = 35   # min score to proceed to SalesAgent
_COMPLETENESS_GATE = 0.2        # at least 1 of 5 key fields must be known

_llm = OllamaLLM(
    model=settings.ollama_model,
    base_url=settings.ollama_base_url,
    temperature=0.1,
    num_ctx=2048,
    repeat_penalty=1.1,
    num_gpu=settings.ollama_num_gpu,
)

# ── Target industries ──────────────────────────────────────────────────────────
_PRIMARY_INDUSTRIES = {"manufacturing", "it services", "healthcare", "retail", "bfsi"}
_ADJACENT_INDUSTRIES = {"automotive", "education", "logistics", "pharma", "fmcg", "real estate"}

# ── HRMS stack classification ──────────────────────────────────────────────────
_MODERN_HRMS = {
    "darwinbox", "keka", "greythr", "sumhr", "bamboohr",
    "workday", "successfactors", "zoho people",
}
_LEGACY_HRMS = {
    "sap hr", "oracle hrms", "peoplesoft", "legacy", "banking hr",
}
_SPREADSHEET = {"excel", "google sheets", "spreadsheet", "manual"}


def qualification_node(state: LeadState) -> LeadState:
    """LangGraph node: score the lead and decide qualification gate."""
    logger.info("[QualificationAgent] scoring '%s'", state.get("company_name", ""))

    errors = list(state.get("errors", []))
    data_completeness = _compute_data_completeness(state)

    breakdown = ScoreBreakdown(
        company_size_fit=score_company_size(state.get("employee_count")),
        industry_relevance=score_industry(state.get("industry", "")),
        tech_stack_gap=score_tech_stack(state.get("tech_stack", [])),
        decision_maker_reachability=score_dm_reachability(state.get("decision_makers", [])),
        growth_signal=score_growth_signal(state.get("growth_signal", "unknown")),
    )

    total = sum(breakdown.values())

    # Gate 1: score threshold. Gate 2: minimum data completeness.
    is_qualified = total >= _QUALIFICATION_THRESHOLD and data_completeness >= _COMPLETENESS_GATE
    status = "qualified" if is_qualified else "disqualified"

    qualification_confidence = round(data_completeness * min(total / 100.0, 1.0), 2)
    reasoning = _generate_reasoning(state, breakdown, total, data_completeness, qualification_confidence)

    logger.info(
        "[QualificationAgent] %s: score=%d confidence=%.2f is_qualified=%s completeness=%.1f",
        state.get("company_name", ""),
        total,
        qualification_confidence,
        is_qualified,
        data_completeness,
    )

    return {
        **state,
        "qualification_score": total,
        "qualification_confidence": qualification_confidence,
        "score_breakdown": breakdown,
        "qualification_reasoning": reasoning,
        "is_qualified": is_qualified,
        "status": status,
        "errors": errors,
    }


# ── Scoring functions (pure, deterministic) ────────────────────────────────────

def score_company_size(employee_count: int | None) -> int:
    if employee_count is None:
        return 8   # mid-range default
    if employee_count <= 50:
        return 2
    if employee_count <= 200:
        return 8
    if employee_count <= 500:
        return 14
    if employee_count <= 2000:
        return 18
    return 20


def score_industry(industry: str) -> int:
    lower = industry.lower().strip()
    if lower in _PRIMARY_INDUSTRIES:
        return 20
    if lower in _ADJACENT_INDUSTRIES:
        return 12
    if lower == "unknown" or not lower:
        return 6
    return 4


def score_tech_stack(tech_stack: list[str]) -> int:
    if not tech_stack:
        return 10   # unknown — cannot distinguish "no HRMS" from "data not extracted"
    combined = " ".join(tech_stack).lower()
    if any(t in combined for t in _MODERN_HRMS):
        return 4    # already on a modern HRMS competitor
    if any(t in combined for t in _LEGACY_HRMS):
        return 12   # legacy system — modernisation opportunity
    if any(t in combined for t in _SPREADSHEET):
        return 18   # spreadsheet/manual — strongest gap
    return 10       # unrecognised stack — moderate gap


def score_dm_reachability(decision_makers: list[dict]) -> int:
    if not decision_makers:
        return 4  # no contact found but company may still be reachable via website
    best = max(decision_makers, key=lambda d: d.get("confidence", 0))
    confidence = max(0.4, best.get("confidence", 0.4))  # floor at 0.4 (title-found baseline)
    has_email = bool(best.get("email"))
    has_linkedin = bool(best.get("linkedin_url"))
    has_name = best.get("name") not in (None, "Unknown", "")

    if has_email and has_linkedin:
        base = 20
    elif has_email or has_linkedin:
        base = 12
    elif has_name:
        base = 6
    else:
        base = 3  # title found but no name or contact info

    return max(1, round(base * confidence))


def score_growth_signal(signal: str) -> int:
    mapping = {
        "hiring_surge": 20,
        "recent_funding": 20,
        "expansion": 20,
        "stable": 10,
        "contracting": 2,
        "unknown": 10,
    }
    return mapping.get(signal.lower(), 10)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _compute_data_completeness(state: LeadState) -> float:
    """0.0–1.0: fraction of the 5 key scoring fields that carry real data."""
    fields = [
        state.get("employee_count") is not None,
        bool(state.get("industry")) and state.get("industry", "").lower() not in ("unknown", ""),
        bool(state.get("hq_location")),
        bool(state.get("decision_makers")),
        state.get("growth_signal", "unknown").lower() != "unknown",
    ]
    return round(sum(fields) / len(fields), 2)


# ── LLM reasoning ──────────────────────────────────────────────────────────────

@retry(stop=stop_after_attempt(1), wait=wait_exponential(multiplier=1, min=1, max=2), reraise=False)
def _invoke_llm(prompt: str) -> str:
    llm_calls.labels(agent="qualification").inc()
    return _llm.invoke(prompt).strip()


def _generate_reasoning(
    state: LeadState, breakdown: ScoreBreakdown, total: int, data_completeness: float,
    qualification_confidence: float,
) -> str:
    try:
        prompt = load_prompt(
            "qualification_reasoning.j2",
            company_name=state.get("company_name") or "Unknown Company",
            industry=state.get("industry") or "Unknown",
            employee_count=state.get("employee_count"),
            hq_location=state.get("hq_location") or None,
            score_breakdown=breakdown,
            qualification_score=total,
            data_completeness=data_completeness,
            qualification_confidence=qualification_confidence,
        )
        return _invoke_llm(prompt)
    except Exception as exc:
        logger.warning("[QualificationAgent] LLM reasoning failed after retries: %s", exc)
        return (
            f"Score: {total}/100 (confidence: {qualification_confidence:.0%}). "
            "Automated qualification completed."
        )
