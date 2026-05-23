"""
SalesAgent node — generates RAG-grounded cold email + LinkedIn message.

Hallucination prevention:
  Layer 1: Constrained prompt instructs LLM to use ONLY provided RAG chunks.
  Layer 2: rag_context_used stored in LeadState — visible in every API response.
"""
import logging
import re

from langchain_ollama import OllamaLLM
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from models.state import LeadState, OutreachEmail
from observability.metrics import llm_calls
from prompts import load_prompt
from rag.retriever import build_retriever, retrieve_chunks

logger = logging.getLogger(__name__)

_MAX_EMAIL_WORDS = 220
_MAX_LINKEDIN_CHARS = 300

_llm = OllamaLLM(
    model=settings.ollama_model,
    base_url=settings.ollama_base_url,
    temperature=0.3,
    num_ctx=2048,
    repeat_penalty=1.1,
    num_gpu=settings.ollama_num_gpu,
)


def sales_node(state: LeadState) -> LeadState:
    """LangGraph node: generate RAG-grounded outreach content."""

    logger.info(
        "[SalesAgent] generating outreach for '%s'",
        state.get("company_name", "")
    )

    # ── RAG retrieval ─────────────────────────────────────
    retriever = build_retriever()
    rag_query = _build_rag_query(state)
    chunks = retrieve_chunks(rag_query, retriever)

    if not chunks:
        logger.warning("[SalesAgent] RAG index empty — outreach not grounded in product facts")

    # ── Primary decision maker ────────────────────────────
    dms = state.get("decision_makers", [])
    primary_dm = dms[0] if dms else {"name": "HR Leadership Team", "title": "HR", "email": None}
    dm_name = primary_dm.get("name") or "HR Leadership Team"
    dm_title = primary_dm.get("title") or "HR"

    # ── Cold email ────────────────────────────────────────
    outreach_email = _generate_email(state, dm_name, dm_title, chunks)

    # ── LinkedIn message ──────────────────────────────────
    linkedin_message = _generate_linkedin(state, dm_name, dm_title, chunks)

    logger.info(
        "[SalesAgent] done: email_words=%d linkedin_chars=%d rag_chunks=%d",
        len(outreach_email["body"].split()),
        len(linkedin_message),
        len(chunks),
    )

    return {
        **state,
        "outreach_email": outreach_email,
        "linkedin_message": linkedin_message,
        "rag_context_used": chunks,
        "status": "qualified",
    }


def _build_rag_query(state: LeadState) -> str:

    parts = []

    company = state.get("company_name")
    industry = state.get("industry")
    tech = state.get("tech_stack", [])
    growth = state.get("growth_signal")
    summary = state.get("raw_summary")

    if company:
        parts.append(company)

    if industry and industry != "Unknown":
        parts.append(f"{industry} HR challenges")

    if tech:
        parts.append(
            "tech stack " + ", ".join(tech)
        )

    if growth and growth != "unknown":
        parts.append(
            f"growth signal {growth}"
        )

    if summary:
        parts.append(summary[:150])

    parts.append(
        "HumanMaximizer HRMS payroll onboarding workforce"
    )

    return " | ".join(parts)


@retry(stop=stop_after_attempt(1), wait=wait_exponential(multiplier=1, min=1, max=2), reraise=False)
def _invoke_llm(prompt: str) -> str:
    llm_calls.labels(agent="sales").inc()
    return _llm.invoke(prompt).strip()


def _generate_email(
    state: LeadState,
    dm_name: str,
    dm_title: str,
    rag_chunks: list[str],
) -> OutreachEmail:
    prompt = load_prompt(
        "cold_email.j2",
        company_name=state.get("company_name", ""),
        industry=state.get("industry", ""),
        employee_count=state.get("employee_count"),
        dm_name=dm_name,
        dm_title=dm_title,
        raw_summary=state.get("raw_summary", ""),
        rag_chunks=rag_chunks or ["HumanMaximizer is an end-to-end HRMS for Indian enterprises."],
    )
    try:
        raw = _invoke_llm(prompt)
        return _parse_email(raw)
    except Exception as exc:
        logger.warning("[SalesAgent] email LLM failed: %s", exc)
        return OutreachEmail(
            subject=f"Streamlining HR at {state.get('company_name', 'your company')}",
            body=(
                f"Dear {dm_name},\n\n"
                f"I noticed {state.get('company_name', 'your company')} "
                f"is operating in {state.get('industry', 'your industry')}.\n\n"
                "HumanMaximizer supports HR, payroll and workforce operations "
                "through a unified HRMS platform.\n\n"
                "If operational efficiency is currently important, "
                "it may be worth exploring fit.\n\n"
                "Regards,\nHumanMaximizer"
            ),
        )


def _generate_linkedin(
    state: LeadState,
    dm_name: str,
    dm_title: str,
    rag_chunks: list[str],
) -> str:
    pain_hook = _extract_pain_hook(state.get("raw_summary", ""), state.get("industry", ""))
    hm_one_liner = (
        rag_chunks[0][:150] if rag_chunks
        else "HumanMaximizer is an end-to-end HRMS for Indian enterprises."
    )

    try:
        prompt = load_prompt(
            "linkedin_message.j2",
            dm_name=dm_name,
            dm_title=dm_title,
            company_name=state.get("company_name") or "your company",
            pain_point_hook=pain_hook,
            hm_one_liner=hm_one_liner,
        )
        response = _invoke_llm(prompt)
        if response:
            return _enforce_linkedin_limit(response)
    except Exception as exc:
        logger.warning("[SalesAgent] linkedin generation failed: %s", exc)

    fallback = (
        f"Hi {dm_name}, I noticed "
        f"{state.get('company_name', 'your company')} "
        "may be evolving HR processes. "
        "HumanMaximizer helps simplify payroll and workforce operations."
    )
    return fallback[:_MAX_LINKEDIN_CHARS]


def _parse_email(raw: str) -> OutreachEmail:
    subject_match = re.search(r"SUBJECT:\s*(.+)", raw, re.IGNORECASE)
    body_match = re.search(r"BODY:\s*\n([\s\S]+)", raw, re.IGNORECASE)

    subject = subject_match.group(1).strip() if subject_match else "Following up on HRMS"
    body = body_match.group(1).strip() if body_match else raw.strip()

    words = body.split()
    if len(words) > _MAX_EMAIL_WORDS:
        truncated = " ".join(words[:_MAX_EMAIL_WORDS])
        last_period = truncated.rfind(".")
        body = truncated[: last_period + 1] if last_period > 100 else truncated

    return OutreachEmail(subject=subject, body=body)


def _enforce_linkedin_limit(msg: str) -> str:
    if len(msg) <= _MAX_LINKEDIN_CHARS:
        return msg
    truncated = msg[:_MAX_LINKEDIN_CHARS]
    last_period = truncated.rfind(".")
    if last_period > 50:
        return truncated[: last_period + 1]
    return truncated.rstrip() + "…"


def _extract_pain_hook(summary: str, industry: str) -> str:
    if not summary:
        return f"scaling HR operations in {industry}" if industry else "scaling HR operations"
    first_period = summary.find(".")
    if first_period > 20:
        return summary[:first_period]
    return summary[:120]
