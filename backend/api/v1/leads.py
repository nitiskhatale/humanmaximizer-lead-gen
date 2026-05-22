"""
GET /api/v1/leads           — list all leads (paginated, status filter)
GET /api/v1/leads/{lead_id} — get a single lead by UUID
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from models import get_session, get_lead_by_uuid, list_leads

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "",
    summary="List qualified leads",
    description=(
        "Returns paginated leads from the database. "
        "Sort by `score` to surface the highest-priority targets first, "
        "or by `created_at` (default) for newest first. "
        "Filter by `status` to view only `qualified`, `disqualified`, `error`, or `pending` leads."
    ),
    tags=["Qualification"],
    responses={
        200: {
            "description": "Paginated lead list",
            "content": {
                "application/json": {
                    "example": {
                        "count": 1,
                        "sort_by": "score",
                        "leads": [
                            {
                                "lead_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                                "company_name": "Bharat Forge Ltd",
                                "industry": "Manufacturing",
                                "qualification_score": 72,
                                "qualification_confidence": 0.72,
                                "is_qualified": True,
                                "status": "qualified",
                            }
                        ],
                    }
                }
            },
        }
    },
)
async def get_leads(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = Query(
        default=None,
        description="Filter by status: `qualified`, `disqualified`, `error`, `pending`",
    ),
    sort_by: Optional[str] = Query(
        default="created_at",
        description="`score` — highest qualification score first. `created_at` — newest first.",
    ),
    session: AsyncSession = Depends(get_session),
):
    leads = await list_leads(session, limit=limit, offset=offset, status=status, sort_by=sort_by)
    return {
        "count": len(leads),
        "sort_by": sort_by,
        "leads": [lead.to_dict() for lead in leads],
    }


@router.get(
    "/{lead_id}",
    summary="Inspect lead by UUID",
    description=(
        "Returns the full lead record including score breakdown, qualification reasoning, "
        "outreach copy, and RAG context used. Use the `lead_id` returned by `POST /search`."
    ),
    tags=["Qualification"],
    responses={
        200: {"description": "Full lead record"},
        404: {
            "description": "Lead not found",
            "content": {"application/json": {"example": {"detail": "Lead 'abc-123' not found"}}},
        },
    },
)
async def get_lead(
    lead_id: str,
    session: AsyncSession = Depends(get_session),
):
    lead = await get_lead_by_uuid(session, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead '{lead_id}' not found")
    return lead.to_dict()
