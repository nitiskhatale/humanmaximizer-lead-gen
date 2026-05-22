import json
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.lead import Lead
from models.state import LeadState


async def save_lead(session: AsyncSession, state: LeadState) -> Lead:
    """
    Insert or update a Lead row from a completed LeadState.

    If the state carries a lead_id (UUID string) from a previous partial
    save, upsert by that UUID to avoid duplicate rows.
    """
    lead_uuid = state.get("lead_id") or str(uuid.uuid4())

    result = await session.execute(
        select(Lead).where(Lead.lead_uuid == lead_uuid)
    )
    lead = result.scalar_one_or_none()

    outreach = state.get("outreach_email")

    if lead is None:
        lead = Lead(lead_uuid=lead_uuid)
        session.add(lead)

    lead.keyword = state.get("keyword", "")
    lead.location = state.get("location", "")
    lead.company_name = state.get("company_name", "")
    lead.domain = state.get("domain", "")
    lead.description = state.get("description", "")
    lead.employee_count = state.get("employee_count")
    lead.industry = state.get("industry", "")
    lead.hq_location = state.get("hq_location", "")
    lead.tech_stack_json = json.dumps(state.get("tech_stack", []))
    lead.decision_makers_json = json.dumps(state.get("decision_makers", []))
    lead.raw_summary = state.get("raw_summary", "")
    lead.growth_signal = state.get("growth_signal", "unknown")
    lead.qualification_score = state.get("qualification_score", 0)
    lead.score_breakdown_json = json.dumps(state.get("score_breakdown", {}))
    lead.qualification_reasoning = state.get("qualification_reasoning", "")
    lead.is_qualified = state.get("is_qualified", False)
    lead.outreach_email_json = json.dumps(outreach) if outreach else None
    lead.linkedin_message = state.get("linkedin_message")
    lead.rag_context_json = json.dumps(state.get("rag_context_used", []))
    lead.status = state.get("status", "pending")
    lead.errors_json = json.dumps(state.get("errors", []))
    lead.processing_time_ms = state.get("processing_time_ms", 0)

    await session.commit()
    await session.refresh(lead)
    return lead


async def get_lead_by_uuid(session: AsyncSession, lead_uuid: str) -> Optional[Lead]:
    """Fetch a lead by its UUID string. Returns None if not found."""
    result = await session.execute(
        select(Lead).where(Lead.lead_uuid == lead_uuid)
    )
    return result.scalar_one_or_none()


async def get_lead_by_id(session: AsyncSession, lead_id: int) -> Optional[Lead]:
    """Fetch a lead by its integer primary key. Returns None if not found."""
    result = await session.execute(
        select(Lead).where(Lead.id == lead_id)
    )
    return result.scalar_one_or_none()


async def list_leads(
    session: AsyncSession,
    limit: int = 20,
    offset: int = 0,
    status: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
) -> list[Lead]:
    """List leads with optional status filter, sort, and pagination.

    sort_by='score'      → qualification_score DESC (highest-ranked leads first)
    sort_by='created_at' → newest first (default)
    """
    order_col = Lead.qualification_score.desc() if sort_by == "score" else Lead.created_at.desc()
    query = select(Lead).order_by(order_col).limit(limit).offset(offset)
    if status:
        query = query.where(Lead.status == status)
    result = await session.execute(query)
    return list(result.scalars().all())
