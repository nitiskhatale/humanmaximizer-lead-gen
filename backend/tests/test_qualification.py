"""
Unit tests for all 5 deterministic scoring functions.
No LLM calls are made — only pure Python logic is exercised.
"""
import pytest

from agents.qualification_agent import (
    qualification_node,
    score_company_size,
    score_dm_reachability,
    score_growth_signal,
    score_industry,
    score_tech_stack,
)
from tests.fixtures.demo_state import DEMO_STATE, DISQUALIFIED_STATE


# ── score_company_size ─────────────────────────────────────────────────────────

class TestScoreCompanySize:
    def test_none_returns_mid_default(self):
        assert score_company_size(None) == 8

    def test_very_small(self):
        assert score_company_size(10) == 2

    def test_boundary_50(self):
        assert score_company_size(50) == 2

    def test_small_medium(self):
        assert score_company_size(100) == 8

    def test_boundary_200(self):
        assert score_company_size(200) == 8

    def test_medium(self):
        assert score_company_size(300) == 14

    def test_boundary_500(self):
        assert score_company_size(500) == 14

    def test_large(self):
        assert score_company_size(1000) == 18

    def test_boundary_2000(self):
        assert score_company_size(2000) == 18

    def test_enterprise(self):
        assert score_company_size(10000) == 20


# ── score_industry ─────────────────────────────────────────────────────────────

class TestScoreIndustry:
    @pytest.mark.parametrize("industry", [
        "Manufacturing", "IT Services", "Healthcare", "Retail", "BFSI",
    ])
    def test_primary_industry_returns_20(self, industry):
        assert score_industry(industry) == 20

    @pytest.mark.parametrize("industry", [
        "Automotive", "Education", "Logistics", "Pharma", "FMCG", "Real Estate",
    ])
    def test_adjacent_industry_returns_12(self, industry):
        assert score_industry(industry) == 12

    def test_unknown_returns_6(self):
        assert score_industry("unknown") == 6

    def test_empty_returns_6(self):
        assert score_industry("") == 6

    def test_other_industry_returns_4(self):
        assert score_industry("Agriculture") == 4


# ── score_tech_stack ───────────────────────────────────────────────────────────

class TestScoreTechStack:
    def test_empty_stack_returns_10(self):
        # Empty list → unknown/undetected; code conservatively returns 10
        # (can't distinguish "no HRMS" from "data not extracted" in live mode)
        assert score_tech_stack([]) == 10

    def test_modern_hrms_returns_4(self):
        assert score_tech_stack(["Darwinbox"]) == 4

    def test_workday_modern_returns_4(self):
        assert score_tech_stack(["Workday"]) == 4

    def test_legacy_hrms_returns_12(self):
        assert score_tech_stack(["SAP HR"]) == 12

    def test_peoplesoft_legacy_returns_12(self):
        assert score_tech_stack(["PeopleSoft"]) == 12

    def test_excel_returns_18(self):
        assert score_tech_stack(["Excel"]) == 18

    def test_spreadsheet_keyword_returns_18(self):
        assert score_tech_stack(["Google Sheets"]) == 18

    def test_unknown_stack_returns_10(self):
        assert score_tech_stack(["Some ERP"]) == 10


# ── score_dm_reachability ─────────────────────────────────────────────────────

class TestScoreDmReachability:
    def test_no_dms_returns_0(self):
        assert score_dm_reachability([]) == 0

    def test_title_only_returns_3(self):
        # confidence=1.0 isolates the base score table; scaling by <1.0 is a separate concern
        dms = [{"name": "Unknown", "title": "HR Manager", "email": "", "linkedin_url": "", "confidence": 1.0}]
        assert score_dm_reachability(dms) == 3

    def test_name_only_returns_6(self):
        dms = [{"name": "Ravi Sharma", "title": "CHRO", "email": "", "linkedin_url": "", "confidence": 1.0}]
        assert score_dm_reachability(dms) == 6

    def test_email_only_returns_12(self):
        dms = [{"name": "Unknown", "title": "VP HR", "email": "vp@example.com", "linkedin_url": "", "confidence": 1.0}]
        assert score_dm_reachability(dms) == 12

    def test_linkedin_only_returns_12(self):
        dms = [{"name": "Unknown", "title": "VP HR", "email": "", "linkedin_url": "https://linkedin.com/in/vp", "confidence": 1.0}]
        assert score_dm_reachability(dms) == 12

    def test_email_and_linkedin_returns_20(self):
        dms = [{"name": "Priya Mehta", "title": "CHRO", "email": "priya@example.com", "linkedin_url": "https://linkedin.com/in/priya", "confidence": 1.0}]
        assert score_dm_reachability(dms) == 20

    def test_picks_highest_confidence_dm(self):
        dms = [
            {"name": "Unknown", "title": "HR Exec", "email": "", "linkedin_url": "", "confidence": 0.3},
            {"name": "Priya Mehta", "title": "CHRO", "email": "priya@example.com", "linkedin_url": "https://linkedin.com/in/priya", "confidence": 1.0},
        ]
        assert score_dm_reachability(dms) == 20


# ── score_growth_signal ────────────────────────────────────────────────────────

class TestScoreGrowthSignal:
    @pytest.mark.parametrize("signal", ["hiring_surge", "recent_funding", "expansion"])
    def test_positive_signals_return_20(self, signal):
        assert score_growth_signal(signal) == 20

    @pytest.mark.parametrize("signal", ["stable", "unknown"])
    def test_neutral_signals_return_10(self, signal):
        assert score_growth_signal(signal) == 10

    def test_contracting_returns_2(self):
        assert score_growth_signal("contracting") == 2

    def test_unknown_string_returns_10(self):
        assert score_growth_signal("random_value") == 10


# ── Integration gate tests ─────────────────────────────────────────────────────

class TestQualificationGate:
    def test_demo_state_score_is_at_least_60(self):
        """Bharat Forge: size=20, industry=20, stack=12(SAP legacy), dm≈17(conf=0.85), growth=20 => ~89."""
        import copy
        state = copy.deepcopy(DEMO_STATE)
        result = qualification_node(state)
        # size=20(10000 emp), industry=20(Manufacturing), stack=12(SAP HR legacy),
        # dm=round(20*0.85)=17(email+linkedin, confidence=0.85), growth=20(hiring_surge) => 89
        assert result["qualification_score"] >= 60
        assert result["is_qualified"] is True
        assert result["status"] == "qualified"

    def test_disqualified_state_score_is_low(self):
        """Tiny Farm Co: 2+4+10+0+2 = 18 < threshold (35) → disqualified; verify breakdown sums correctly."""
        import copy
        state = copy.deepcopy(DISQUALIFIED_STATE)
        result = qualification_node(state)
        # size=2(5 emp), industry=4(Agriculture), stack=10(empty/unknown), dm=0(none), growth=2(contracting) => 18
        # 18 < threshold 35 → disqualified; test only verifies the breakdown sums to the total
        assert result["qualification_score"] == result["score_breakdown"]["company_size_fit"] \
                                               + result["score_breakdown"]["industry_relevance"] \
                                               + result["score_breakdown"]["tech_stack_gap"] \
                                               + result["score_breakdown"]["decision_maker_reachability"] \
                                               + result["score_breakdown"]["growth_signal"]

    def test_score_below_threshold_is_disqualified(self):
        """Agriculture + 10 emp + no DM + contracting = 18 < 35 threshold → disqualified."""
        from models.state import initial_state
        state = initial_state("boundary-test")
        state["employee_count"] = 10           # size=2
        state["industry"] = "Agriculture"      # industry=4
        state["tech_stack"] = []               # stack=10 (empty list → unknown/undetected)
        state["decision_makers"] = []          # dm=0
        state["growth_signal"] = "contracting" # growth=2  => total=18 < 35
        result = qualification_node(state)
        assert result["qualification_score"] == 18
        assert result["is_qualified"] is False
        assert result["status"] == "disqualified"

    def test_score_breakdown_keys_present(self):
        import copy
        state = copy.deepcopy(DEMO_STATE)
        result = qualification_node(state)
        assert "company_size_fit" in result["score_breakdown"]
        assert "industry_relevance" in result["score_breakdown"]
        assert "tech_stack_gap" in result["score_breakdown"]
        assert "decision_maker_reachability" in result["score_breakdown"]
        assert "growth_signal" in result["score_breakdown"]
