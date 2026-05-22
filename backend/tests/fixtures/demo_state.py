"""
Pre-built LeadState fixtures for tests that need realistic data.
No LLM calls needed — all fields populated statically.
"""
from models.state import LeadState

DEMO_STATE: LeadState = {
    "lead_id": "test-bharat-forge-001",
    "keyword": "manufacturing companies Pune",
    "location": "Pune, India",
    "company_name": "Bharat Forge",
    "domain": "bharatforge.com",
    "description": (
        "Bharat Forge is one of the world's largest forging companies, "
        "headquartered in Pune. It serves automotive, aerospace, and industrial sectors."
    ),
    "employee_count": 10000,
    "industry": "Manufacturing",
    "hq_location": "Pune, India",
    "tech_stack": ["SAP HR"],
    "decision_makers": [
        {
            "name": "Rajesh Kumar",
            "title": "VP HR",
            "email": "rajesh.kumar@bharatforge.com",
            "linkedin_url": "https://linkedin.com/in/rajeshkumar",
            "confidence": 0.85,
        }
    ],
    "raw_summary": (
        "COMPANY OVERVIEW: Bharat Forge is a Pune-based global forging leader "
        "with ~10,000 employees across manufacturing and industrial segments.\n\n"
        "HR PAIN POINTS: Running SAP HR which is expensive to maintain. "
        "Compliance overhead at scale.\n\n"
        "HRMS FIT SIGNAL: Strong fit — large workforce, legacy HR system, "
        "manufacturing sector is primary target."
    ),
    "growth_signal": "hiring_surge",
    "qualification_score": 0,
    "score_breakdown": {},
    "qualification_reasoning": "",
    "is_qualified": False,
    "outreach_email": None,
    "linkedin_message": None,
    "rag_context_used": [],
    "status": "pending",
    "errors": [],
    "processing_time_ms": 0,
}

DISQUALIFIED_STATE: LeadState = {
    "lead_id": "test-tiny-farm-001",
    "keyword": "small farms rural",
    "location": "Rural India",
    "company_name": "Tiny Farm Co",
    "domain": "tinyfarm.in",
    "description": "A very small family-run farm with a handful of seasonal workers.",
    "employee_count": 5,
    "industry": "Agriculture",
    "hq_location": "Rural Maharashtra",
    "tech_stack": [],
    "decision_makers": [],
    "raw_summary": "Small family farm, no formal HR system needed.",
    "growth_signal": "contracting",
    "qualification_score": 0,
    "score_breakdown": {},
    "qualification_reasoning": "",
    "is_qualified": False,
    "outreach_email": None,
    "linkedin_message": None,
    "rag_context_used": [],
    "status": "pending",
    "errors": [],
    "processing_time_ms": 0,
}
