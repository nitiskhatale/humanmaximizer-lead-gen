import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.database import Base


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_uuid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)

    # Search context
    keyword: Mapped[str] = mapped_column(String(500), default="")
    location: Mapped[str] = mapped_column(String(200), default="")

    # Company info
    company_name: Mapped[str] = mapped_column(String(500), default="")
    domain: Mapped[str] = mapped_column(String(500), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    employee_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    industry: Mapped[str] = mapped_column(String(200), default="")
    hq_location: Mapped[str] = mapped_column(String(200), default="")
    tech_stack_json: Mapped[str] = mapped_column(Text, default="[]")
    decision_makers_json: Mapped[str] = mapped_column(Text, default="[]")
    raw_summary: Mapped[str] = mapped_column(Text, default="")
    growth_signal: Mapped[str] = mapped_column(String(50), default="unknown")

    # Qualification
    qualification_score: Mapped[int] = mapped_column(Integer, default=0)
    score_breakdown_json: Mapped[str] = mapped_column(Text, default="{}")
    qualification_reasoning: Mapped[str] = mapped_column(Text, default="")
    is_qualified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Outreach
    outreach_email_json: Mapped[str] = mapped_column(Text, nullable=True)
    linkedin_message: Mapped[str] = mapped_column(Text, nullable=True)
    rag_context_json: Mapped[str] = mapped_column(Text, default="[]")

    # Metadata
    status: Mapped[str] = mapped_column(String(20), default="pending")
    errors_json: Mapped[str] = mapped_column(Text, default="[]")
    processing_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # ── JSON convenience properties ────────────────────────

    @property
    def tech_stack(self) -> list:
        return json.loads(self.tech_stack_json or "[]")

    @property
    def decision_makers(self) -> list:
        return json.loads(self.decision_makers_json or "[]")

    @property
    def score_breakdown(self) -> dict:
        return json.loads(self.score_breakdown_json or "{}")

    @property
    def outreach_email(self) -> Optional[dict]:
        if not self.outreach_email_json:
            return None
        return json.loads(self.outreach_email_json)

    @property
    def rag_context_used(self) -> list:
        return json.loads(self.rag_context_json or "[]")

    @property
    def errors(self) -> list:
        return json.loads(self.errors_json or "[]")

    @property
    def qualification_confidence(self) -> float:
        """Derived: data completeness × score strength. Consistent with QualificationAgent logic."""
        fields_known = [
            self.employee_count is not None,
            bool(self.industry) and self.industry.lower() not in ("unknown", ""),
            bool(self.hq_location),
            len(self.decision_makers) > 0,
            self.growth_signal.lower() != "unknown",
        ]
        completeness = sum(fields_known) / len(fields_known)
        return round(completeness * min(self.qualification_score / 100.0, 1.0), 2)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "lead_id": self.lead_uuid,
            "keyword": self.keyword,
            "location": self.location,
            "company_name": self.company_name,
            "domain": self.domain,
            "description": self.description,
            "employee_count": self.employee_count,
            "industry": self.industry,
            "hq_location": self.hq_location,
            "tech_stack": self.tech_stack,
            "decision_makers": self.decision_makers,
            "raw_summary": self.raw_summary,
            "growth_signal": self.growth_signal,
            "qualification_score": self.qualification_score,
            "qualification_confidence": self.qualification_confidence,
            "score_breakdown": self.score_breakdown,
            "qualification_reasoning": self.qualification_reasoning,
            "is_qualified": self.is_qualified,
            "outreach_email": self.outreach_email,
            "linkedin_message": self.linkedin_message,
            "rag_context_used": self.rag_context_used,
            "status": self.status,
            "errors": self.errors,
            "processing_time_ms": self.processing_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
