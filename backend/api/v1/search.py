"""
POST /api/v1/search — run the full 3-agent pipeline for a keyword/company search.

Single-company mode (max_leads=1, default):
  Returns one fully enriched lead — backward-compatible with the original response shape.

Multi-company mode (max_leads 2–10):
  Searches once, scrapes and extracts data for each result, runs Qualification and Sales
  on every candidate, then returns them ranked by qualification_score descending.
"""
import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from agents import pipeline
from agents.qualification_agent import qualification_node
from agents.research_agent import generate_summary, research_all_candidates
from agents.sales_agent import sales_node
from models import get_session, save_lead
from models.state import LeadState, initial_state
from observability.metrics import leads_processed, pipeline_duration, qualification_score_dist, rag_chunks_retrieved

logger = logging.getLogger(__name__)
router = APIRouter()


class SearchRequest(BaseModel):
    keyword: str
    location: str = ""
    max_leads: int = Field(
        default=5,
        ge=1,
        le=10,
        description=(
            "Number of companies to find and rank. "
            "Set to 1 for single-company mode (original behaviour). "
            "2–10 returns multiple leads ranked by qualification_score."
        ),
    )

    model_config = {"json_schema_extra": {
        "examples": [
            {
                "summary": "Manufacturing — Pune (5 leads)",
                "value": {"keyword": "manufacturing companies", "location": "Pune, India", "max_leads": 5},
            },
            {
                "summary": "Healthcare — Mumbai (5 leads)",
                "value": {"keyword": "healthcare companies", "location": "Mumbai, India", "max_leads": 5},
            },
            {
                "summary": "Single company mode",
                "value": {"keyword": "manufacturing companies", "location": "Pune, India", "max_leads": 1},
            },
        ]
    }}


_SEARCH_RESPONSE_200 = {
    "description": "Pipeline completed — leads qualified or disqualified, ranked by score",
    "content": {
        "application/json": {
            "example": {
                "total": 3,
                "keyword": "manufacturing companies",
                "location": "Pune, India",
                "ranked_by": "qualification_score",
                "leads": [
                    {
                        "rank": 1,
                        "lead_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "db_id": 1,
                        "lead": {
                            "company_name": "Bharat Forge Ltd",
                            "qualification_score": 72,
                            "qualification_confidence": 0.72,
                            "is_qualified": True,
                            "status": "qualified",
                        },
                    },
                    {
                        "rank": 2,
                        "lead_id": "9ab12c34-1234-5678-abcd-ef0123456789",
                        "db_id": 2,
                        "lead": {
                            "company_name": "Kalyani Steels",
                            "qualification_score": 54,
                            "qualification_confidence": 0.48,
                            "is_qualified": True,
                            "status": "qualified",
                        },
                    },
                ],
            }
        }
    },
}


@router.post(
    "/search",
    summary="Discover and qualify B2B leads",
    description=(
        "Runs the full Research → Qualification → Sales agent pipeline for the given "
        "keyword and location.\n\n"
        "`max_leads` (1–10, default 5) controls how many companies are found and processed. "
        "All leads are returned **ranked by `qualification_score` descending** — the most "
        "HRMS-ready prospect is always first.\n\n"
        "**`qualification_confidence`** (0.0–1.0) reflects how much real data backed the "
        "score. Leads with fewer than 2 of 5 key fields populated are never marked "
        "`is_qualified=true`.\n\n"
        "Set `max_leads=1` to replicate the original single-company response."
    ),
    tags=["Lead Discovery"],
    responses={200: _SEARCH_RESPONSE_200},
)
async def run_search(
    body: SearchRequest,
    session: AsyncSession = Depends(get_session),
):
    t0 = time.time()

    if body.max_leads == 1:
        return await _run_single(body, session, t0)
    return await _run_multi(body, session, t0)


# ── Single-company path (original behaviour) ──────────────────────────────────

async def _run_single(body: SearchRequest, session: AsyncSession, t0: float) -> dict:
    state = initial_state(keyword=body.keyword, location=body.location)
    try:
        result = pipeline.invoke(state)
    except Exception as exc:
        logger.error("Pipeline failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pipeline error: {exc}") from exc

    if not result.get("processing_time_ms"):
        result["processing_time_ms"] = int((time.time() - t0) * 1000)

    lead = await save_lead(session, result)
    result["lead_id"] = lead.lead_uuid

    status = result.get("status", "error")
    leads_processed.labels(status=status).inc()
    pipeline_duration.observe(result.get("processing_time_ms", 0) / 1000)
    qualification_score_dist.observe(result.get("qualification_score", 0))
    rag_chunks_retrieved.observe(len(result.get("rag_context_used", [])))

    return {
        "total": 1,
        "keyword": body.keyword,
        "location": body.location,
        "ranked_by": "qualification_score",
        "leads": [{"rank": 1, "lead_id": lead.lead_uuid, "db_id": lead.id, "lead": result}],
    }


# ── Multi-company path ─────────────────────────────────────────────────────────

async def _run_multi(body: SearchRequest, session: AsyncSession, t0: float) -> dict:
    try:
        candidates = research_all_candidates(body.keyword, body.location, body.max_leads)
    except Exception as exc:
        logger.error("research_all_candidates failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {exc}") from exc

    base = initial_state(keyword=body.keyword, location=body.location)
    leads_out: list[dict] = []

    for candidate in candidates:
        company_state: LeadState = {
            **base,
            **candidate,
            "lead_id": str(uuid.uuid4()),
            "processing_time_ms": 0,
        }

        # LLM research summary
        try:
            company_state["raw_summary"] = generate_summary(candidate)
        except Exception as exc:
            logger.warning(
                "[search] LLM summary failed for %s: %s",
                candidate.get("company_name"), exc,
            )
            company_state["raw_summary"] = ""

        # Deterministic qualification scoring + LLM reasoning
        company_state = qualification_node(company_state)

        # Sales copy — only for qualified leads
        if company_state.get("is_qualified", False):
            try:
                company_state = sales_node(company_state)
            except Exception as exc:
                logger.warning(
                    "[search] Sales agent failed for %s: %s",
                    candidate.get("company_name"), exc,
                )

        company_state["processing_time_ms"] = int((time.time() - t0) * 1000)

        try:
            lead = await save_lead(session, company_state)
            company_state["lead_id"] = lead.lead_uuid
            db_id = lead.id
        except Exception as exc:
            logger.error(
                "[search] DB save failed for %s: %s",
                candidate.get("company_name"), exc,
            )
            db_id = None

        status = company_state.get("status", "error")
        leads_processed.labels(status=status).inc()
        qualification_score_dist.observe(company_state.get("qualification_score", 0))
        rag_chunks_retrieved.observe(len(company_state.get("rag_context_used", [])))

        leads_out.append({
            "lead_id": company_state.get("lead_id"),
            "db_id": db_id,
            "lead": company_state,
        })

    # Rank by qualification_score descending
    leads_out.sort(key=lambda x: x["lead"].get("qualification_score", 0), reverse=True)
    for i, item in enumerate(leads_out, start=1):
        item["rank"] = i

    pipeline_duration.observe(time.time() - t0)

    return {
        "total": len(leads_out),
        "keyword": body.keyword,
        "location": body.location,
        "ranked_by": "qualification_score",
        "leads": leads_out,
    }
