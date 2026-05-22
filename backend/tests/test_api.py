"""
Integration tests for FastAPI endpoints.
Uses in-memory SQLite (set in conftest.py) and ASGI transport — no real server needed.
LLM calls will fall back gracefully because Ollama is not running in test environment.
"""
import pytest


class TestHealth:
    async def test_health_returns_200(self, client):
        response = await client.get("/health")
        assert response.status_code == 200

    async def test_health_body(self, client):
        response = await client.get("/health")
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "humanmaximizer-lead-gen"
        assert "llm_model" in data


class TestSearchEndpoint:
    async def test_post_search_returns_lead_id(self, client):
        payload = {"keyword": "manufacturing companies Pune", "location": "Pune, India"}
        response = await client.post("/api/v1/search", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "lead_id" in data
        assert isinstance(data["lead_id"], str)
        assert len(data["lead_id"]) > 0

    async def test_post_search_returns_db_id(self, client):
        payload = {"keyword": "IT services", "location": "Bangalore"}
        response = await client.post("/api/v1/search", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "db_id" in data
        assert isinstance(data["db_id"], int)

    async def test_post_search_returns_lead_object(self, client):
        payload = {"keyword": "healthcare", "location": "Mumbai"}
        response = await client.post("/api/v1/search", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "lead" in data
        lead = data["lead"]
        assert "company_name" in lead
        assert "qualification_score" in lead


class TestLeadsEndpoint:
    async def test_get_lead_by_id_returns_200(self, client):
        # Create a lead first
        payload = {"keyword": "retail bangalore", "location": "Bangalore"}
        post_resp = await client.post("/api/v1/search", json=payload)
        assert post_resp.status_code == 200
        lead_id = post_resp.json()["lead_id"]

        # Then fetch it
        get_resp = await client.get(f"/api/v1/leads/{lead_id}")
        assert get_resp.status_code == 200

    async def test_get_lead_by_id_returns_correct_lead(self, client):
        payload = {"keyword": "bfsi companies", "location": "Mumbai"}
        post_resp = await client.post("/api/v1/search", json=payload)
        lead_id = post_resp.json()["lead_id"]

        get_resp = await client.get(f"/api/v1/leads/{lead_id}")
        data = get_resp.json()
        assert data["lead_id"] == lead_id

    async def test_get_lead_unknown_id_returns_404(self, client):
        response = await client.get("/api/v1/leads/nonexistent-id-xyz")
        assert response.status_code == 404

    async def test_list_leads_returns_200(self, client):
        response = await client.get("/api/v1/leads")
        assert response.status_code == 200
        data = response.json()
        assert "leads" in data
        assert isinstance(data["leads"], list)

    async def test_list_leads_sort_by_score(self, client):
        # Seed a couple of leads
        for kw in ["manufacturing Pune", "IT services Bangalore"]:
            await client.post("/api/v1/search", json={"keyword": kw, "location": "India"})
        response = await client.get("/api/v1/leads?sort_by=score&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert data["sort_by"] == "score"
        scores = [lead["qualification_score"] for lead in data["leads"]]
        assert scores == sorted(scores, reverse=True)

    async def test_list_leads_status_filter(self, client):
        response = await client.get("/api/v1/leads?status=qualified")
        assert response.status_code == 200
        data = response.json()
        for lead in data["leads"]:
            assert lead["status"] == "qualified"


class TestEdgeCases:
    async def test_empty_keyword_still_returns_lead(self, client):
        """Empty keyword still triggers the pipeline via SerpAPI."""
        response = await client.post("/api/v1/search", json={"keyword": "", "location": ""})
        assert response.status_code == 200
        data = response.json()
        assert "lead_id" in data
        assert isinstance(data["lead_id"], str)

    async def test_very_long_keyword_is_handled(self, client):
        long_kw = "HRMS software " * 50
        response = await client.post("/api/v1/search", json={"keyword": long_kw, "location": "India"})
        assert response.status_code == 200

    async def test_duplicate_search_creates_new_lead(self, client):
        """Each pipeline run produces a distinct lead UUID (no accidental deduplication)."""
        payload = {"keyword": "manufacturing Pune", "location": "Pune"}
        r1 = await client.post("/api/v1/search", json=payload)
        r2 = await client.post("/api/v1/search", json=payload)
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["lead_id"] != r2.json()["lead_id"]

    async def test_lead_contains_score_breakdown(self, client):
        """Every qualified lead must carry all 5 scoring dimensions."""
        r = await client.post("/api/v1/search", json={"keyword": "healthcare Mumbai", "location": "Mumbai"})
        assert r.status_code == 200
        lead = r.json()["lead"]
        sb = lead.get("score_breakdown", {})
        for key in ("company_size_fit", "industry_relevance", "tech_stack_gap",
                    "decision_maker_reachability", "growth_signal"):
            assert key in sb, f"Missing score dimension: {key}"

    async def test_rag_query_endpoint_returns_gracefully_when_empty(self, client):
        """RAG query endpoint returns empty chunks list when ChromaDB is not populated."""
        # ChromaDB is not running in tests — verifies graceful degradation path
        response = await client.get("/api/v1/rag/query?q=payroll+compliance")
        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "chunks" in data

    async def test_outreach_missing_lead_returns_404(self, client):
        response = await client.post(
            "/api/v1/outreach/generate",
            json={"lead_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert response.status_code == 404
