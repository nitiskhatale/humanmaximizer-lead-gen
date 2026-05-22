from typing import List, Optional, TypedDict


class DecisionMaker(TypedDict):
    name: str
    title: str
    email: Optional[str]
    linkedin_url: Optional[str]
    confidence: float


class ScoreBreakdown(TypedDict):
    company_size_fit: int
    industry_relevance: int
    tech_stack_gap: int
    decision_maker_reachability: int
    growth_signal: int


class OutreachEmail(TypedDict):
    subject: str
    body: str


class LeadState(TypedDict):
    # ── Input ──────────────────────────────────────────────
    keyword: str
    location: str

    # ── Research Agent outputs ─────────────────────────────
    company_name: str
    domain: str
    description: str
    employee_count: Optional[int]
    industry: str
    hq_location: str
    tech_stack: List[str]
    decision_makers: List[DecisionMaker]
    raw_summary: str
    growth_signal: str   # "hiring_surge"|"recent_funding"|"expansion"|"stable"|"contracting"|"unknown"

    # ── Qualification Agent outputs ────────────────────────
    qualification_score: int         # 0–100
    qualification_confidence: float  # 0.0–1.0: data completeness × score strength
    score_breakdown: ScoreBreakdown
    qualification_reasoning: str
    is_qualified: bool

    # ── Sales Agent outputs ────────────────────────────────
    outreach_email: Optional[OutreachEmail]
    linkedin_message: Optional[str]
    rag_context_used: List[str]      # retrieved chunk texts for citation

    # ── Metadata ───────────────────────────────────────────
    lead_id: Optional[str]           # UUID, assigned on DB insert
    status: str                      # "pending"|"qualified"|"disqualified"|"error"
    errors: List[str]
    processing_time_ms: int


def initial_state(keyword: str, location: str = "") -> LeadState:
    """Return a blank LeadState for the start of a pipeline run."""
    return LeadState(
        keyword=keyword,
        location=location,
        company_name="",
        domain="",
        description="",
        employee_count=None,
        industry="",
        hq_location="",
        tech_stack=[],
        decision_makers=[],
        raw_summary="",
        growth_signal="unknown",
        qualification_score=0,
        qualification_confidence=0.0,
        score_breakdown=ScoreBreakdown(
            company_size_fit=0,
            industry_relevance=0,
            tech_stack_gap=0,
            decision_maker_reachability=0,
            growth_signal=0,
        ),
        qualification_reasoning="",
        is_qualified=False,
        outreach_email=None,
        linkedin_message=None,
        rag_context_used=[],
        lead_id=None,
        status="pending",
        errors=[],
        processing_time_ms=0,
    )
