"""
POST /api/v1/outreach/generate — re-run SalesAgent on an existing lead.

Useful when:
  - The RAG index was refreshed and new product content should be used.
  - The evaluator wants to see outreach regenerated independently.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from agents.sales_agent import sales_node
from models import get_session, get_lead_by_uuid, save_lead

logger = logging.getLogger(__name__)
router = APIRouter()


class OutreachRequest(BaseModel):
    lead_id: str

    model_config = {"json_schema_extra": {
        "examples": [
            {
                "summary": "Valid — use UUID from POST /search response",
                "value": {"lead_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"},
            }
        ]
    }}


@router.post(
    "/generate",
    summary="Generate personalised outreach for a qualified lead",
    description=(
        "Loads a lead by UUID, re-runs the SalesAgent (ChromaDB cosine similarity retrieval + "
        "Mistral-7B generation), and returns a personalised cold email and LinkedIn "
        "message grounded in HumanMaximizer product knowledge.\n\n"
        "`rag_context_used` in the response lists the exact product knowledge chunks "
        "that grounded the generated copy — useful for verifying RAG quality."
    ),
    tags=["Outreach"],
    responses={
        200: {
            "description": "Outreach generated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "lead_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "outreach_email": {
                            "subject": "Modernise HR at Bharat Forge — HumanMaximizer",
                            "body": "Hi [Name], I noticed Bharat Forge is currently on SAP HR...",
                        },
                        "linkedin_message": "Hi [Name], saw that Bharat Forge is scaling rapidly...",
                        "rag_context_used": ["HumanMaximizer payroll automation feature...", "..."],
                    }
                }
            },
        },
        404: {
            "description": "Lead not found",
            "content": {"application/json": {"example": {"detail": "Lead 'abc-123' not found"}}},
        },
        500: {
            "description": "SalesAgent error",
            "content": {"application/json": {"example": {"detail": "SalesAgent error: Ollama unreachable"}}},
        },
    },
)
async def generate_outreach(
    body: OutreachRequest,
    session: AsyncSession = Depends(get_session),
):
    lead = await get_lead_by_uuid(session, body.lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead '{body.lead_id}' not found")

    state = lead.to_dict()
    state["lead_id"] = lead.lead_uuid

    try:
        updated_state = sales_node(state)
    except Exception as exc:
        logger.error("SalesAgent failed for lead %s: %s", body.lead_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"SalesAgent error: {exc}") from exc

    await save_lead(session, updated_state)

    return {
        "lead_id": body.lead_id,
        "outreach_email": updated_state.get("outreach_email"),
        "linkedin_message": updated_state.get("linkedin_message"),
        "rag_context_used": updated_state.get("rag_context_used", []),
    }
