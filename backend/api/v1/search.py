"""
POST /api/v1/search — run the full 3-agent pipeline for a keyword/company search.

It:
  1. Builds an initial LeadState from the request body
  2. Invokes the LangGraph pipeline (Research → Qualification → Sales)
  3. Persists the result to SQLite
  4. Returns the full LeadState JSON + DB-assigned lead_id
"""
import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from agents import pipeline
from models import get_session, save_lead
from models.state import initial_state
from observability.metrics import leads_processed, pipeline_duration, qualification_score_dist, rag_chunks_retrieved

logger = logging.getLogger(__name__)
router = APIRouter()


class SearchRequest(BaseModel):
    keyword: str
    location: str = ""

    model_config = {"json_schema_extra": {
        "examples": [
            {
                "summary": "Manufacturing — Pune",
                "value": {"keyword": "manufacturing companies", "location": "Pune, India"},
            },
            {
                "summary": "Healthcare — Mumbai",
                "value": {"keyword": "healthcare companies", "location": "Mumbai, India"},
            },
        ]
    }}


_SEARCH_RESPONSE_200 = {
    "description": "Pipeline completed — lead qualified or disqualified",
    "content": {
        "application/json": {
            "example": {
                "lead_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "db_id": 1,
                "lead": {
                    "company_name": "Bharat Forge Ltd",
                    "domain": "bharatforge.com",
                    "description": "One of India's largest auto-component manufacturers, headquartered in Pune.",
                    "employee_count": 10000,
                    "industry": "Manufacturing",
                    "hq_location": "Pune, Maharashtra",
                    "qualification_score": 72,
                    "qualification_confidence": 0.72,
                    "is_qualified": True,
                    "status": "qualified",
                },
            }
        }
    },
}

_SEARCH_RESPONSE_422 = {
    "description": "Validation error — `keyword` is required",
    "content": {
        "application/json": {
            "example": {
                "detail": [
                    {"loc": ["body", "keyword"], "msg": "field required", "type": "value_error.missing"}
                ]
            }
        }
    },
}

_SEARCH_RESPONSE_500 = {
    "description": "Pipeline execution error",
    "content": {"application/json": {"example": {"detail": "Pipeline error: SerpAPI error: ..."}}}
}


@router.post(
    "/search",
    summary="Discover and qualify a B2B lead",
    description=(
        "Runs the full Research → Qualification → Sales agent pipeline for the given "
        "keyword and location.\n\n"
        "Returns a fully enriched lead with qualification score, confidence rating, "
        "score breakdown, and personalised outreach copy — persisted to the database.\n\n"
        "**`qualification_confidence`** (0.0–1.0) reflects how much real data backed the "
        "score. Leads with fewer than 2 of 5 key fields populated are never marked "
        "`is_qualified=true`."
    ),
    tags=["Lead Discovery"],
    responses={200: _SEARCH_RESPONSE_200, 422: _SEARCH_RESPONSE_422, 500: _SEARCH_RESPONSE_500},
)
async def run_search(
    body: SearchRequest,
    session: AsyncSession = Depends(get_session),
):
    t0 = time.time()
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
        "lead_id": lead.lead_uuid,
        "db_id": lead.id,
        "lead": result,
    }
