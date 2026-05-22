# HumanMaximizer AI Lead Generation & Research Assistant

AI-powered B2B lead research and outreach generation for the HumanMaximizer HRMS platform. Built with a 3-agent LangGraph pipeline, RAG-grounded outreach, and local LLM inference via Ollama.

---

## Quickstart (5 commands)

```bash
# 1. Clone and enter the project
git clone https://github.com/<your-username>/humanmaximizer-lead-gen.git humanmaximizer-lead-gen && cd humanmaximizer-lead-gen

# 2. Copy environment config
cp .env.example .env

# 3. Start all services (Ollama + ChromaDB + FastAPI)
docker compose up -d

# 4. Pull the LLM and embed model, then ingest website content
docker compose exec ollama ollama pull mistral:7b-instruct-v0.3-q4_K_M
docker compose exec ollama ollama pull nomic-embed-text
docker compose exec api python scripts/ingest.py

# 5. Open the API docs
open http://localhost:8000/docs
```

> **CPU-only fallback:** Remove the `deploy.resources.reservations.devices` block in `docker-compose.yml` before running `docker compose up`.

---

## Demo Walkthrough (Swagger UI)

Open `http://localhost:8000/docs` and execute these 4 steps in order:

### Step 1 — Run the pipeline
```
POST /api/v1/search
{
  "keyword": "manufacturing companies Pune",
  "location": "Pune, India"
}
```
Returns `lead_id`, `qualification_score`, and full `lead` object.

### Step 2 — Inspect the full LeadState
```
GET /api/v1/leads/{lead_id}
```
Shows all research data, score breakdown, and qualification reasoning.

### Step 3 — Generate RAG-grounded outreach
```
POST /api/v1/outreach/generate
{
  "lead_id": "<lead_id from step 1>"
}
```
Returns `outreach_email.subject`, `outreach_email.body`, `linkedin_message`, and `rag_context_used`.

### Step 4 — Debug ChromaDB retrieval
```
GET /api/v1/rag/query?q=payroll+compliance+manufacturing
```
Shows raw retrieved chunks from the ChromaDB collection.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama endpoint |
| `OLLAMA_MODEL` | `mistral:7b-instruct-v0.3-q4_K_M` | LLM model tag |
| `CHROMA_HOST` | `localhost` | ChromaDB host |
| `CHROMA_PORT` | `8001` | ChromaDB port |
| `CHROMA_COLLECTION` | `humanmaximizer_knowledge` | ChromaDB collection name |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/leads.db` | SQLite database path |
| `SERPAPI_KEY` | _(empty)_ | SerpAPI key for live company search |
| `LANGCHAIN_API_KEY` | _(empty)_ | LangSmith tracing key |
| `APP_ENV` | `development` | `development` or `production` |
| `LOG_LEVEL` | `INFO` | Python logging level |

---

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI 0.111 + Uvicorn |
| Orchestration | LangGraph 0.1.19 |
| LLM | Mistral-7B-Instruct-v0.3 Q4_K_M via Ollama |
| Embeddings | nomic-embed-text via Ollama |
| Vector DB | ChromaDB 0.6.x (PersistentClient) |
| Database | SQLite + SQLAlchemy async + aiosqlite |
| Migrations | Alembic |
| Observability | Prometheus + LangSmith |
| Scraping | httpx + BeautifulSoup4 |
| Templating | Jinja2 (StrictUndefined) |
| Testing | pytest + pytest-asyncio + httpx ASGI |
| Containerisation | Docker Compose |

---

## Running Tests

```bash
cd backend
pytest tests/ -v
```

All tests run without Ollama or ChromaDB — the qualification scoring tests are pure Python and the API tests use an in-memory SQLite database.

---

## Prompt Examples

All prompts are Jinja2 templates in `backend/prompts/`. Below are representative examples
of what each agent sends to Mistral-7B.

### ResearchAgent — `research_summary.j2`

```
Company: Bharat Forge
Domain: bharatforge.com
Industry: Manufacturing
Employees: 10000
Location: Pune, Maharashtra
Current HR Tech: SAP HR, Oracle HRMS

Write a 3-paragraph lead summary...
```

Expected output:
```
COMPANY OVERVIEW: Bharat Forge is one of India's largest auto-component manufacturers...
HR PAIN POINTS: With 10,000 employees across plants, Bharat Forge faces multi-site
payroll complexity, contract-labour compliance under CLRA, and high-volume attendance...
HRMS FIT SIGNAL: Strong candidate — large manufacturing workforce with a legacy SAP HR
system that is expensive to maintain and lacks mobile-first capabilities...
```

### QualificationAgent — `qualification_reasoning.j2`

```
Company: Metropolis Healthcare (Healthcare, 4000 employees)
Score Breakdown:
- Company Size Fit:             18/20
- Industry Relevance:           20/20
- Tech Stack Gap:               18/20
- Decision Maker Reachability:  12/20
- Growth Signal:                20/20
Total: 88/100
```

Expected output:
```
Metropolis's Excel-based HR for 4,000 employees across 200 labs is the strongest
tech-stack gap signal (18/20), combined with active expansion (20/20 growth).
The primary risk is limited decision-maker reachability — no LinkedIn profile found,
restricting outreach to email-only.
```

### SalesAgent — `cold_email.j2`

```
Lead: Metropolis Healthcare, Healthcare, 4000 employees
Decision Maker: Priya Mehta, CHRO
RAG Context: "HumanMaximizer supports multi-state statutory compliance including
PF, ESIC, and PT returns with automated form generation..."
```

Expected output:
```
SUBJECT: Simplify Multi-Lab HR Compliance at Metropolis Healthcare

BODY:
Dear Priya,

Managing HR for 4,000 employees across 200 labs with Excel means every statutory
filing cycle is a manual marathon. HumanMaximizer automates PF, ESIC, and PT
returns across all states from a single dashboard — no reconciliation required.

We've helped similar diagnostics chains cut payroll processing time by centralising
multi-location attendance and leave data. I'd love to show you a 15-minute demo
tailored for your expansion into tier-2 cities. Are you free Thursday afternoon?

Best regards,
HumanMaximizer Sales Team
```

### SalesAgent — `linkedin_message.j2`

```
Recipient: Priya Mehta, CHRO at Metropolis Healthcare
Hook: Managing HR for 200 labs through Excel is creating compliance risk
HM one-liner: HumanMaximizer automates statutory filings for multi-location Indian enterprises
```

Expected output:
```
Hi Priya, scaling Metropolis across 200 labs while managing statutory compliance
on Excel must be a real challenge. HumanMaximizer helps diagnostics chains
automate this end-to-end. Would you be open to a quick chat?
```

---

## Lead Ranking

Use the `sort_by=score` query parameter to get leads ranked by relevance (highest qualification score first):

```
GET /api/v1/leads?sort_by=score&limit=10&status=qualified
```

Response includes `sort_by` field and leads ordered by `qualification_score` descending.

---

## Architecture PDF

Generate the PDF deliverable from Markdown source:

```bash
# From project root
make pdf
# Output: docs/architecture.pdf
```

Requires: `pip install reportlab` (included in requirements.txt)

---

## Project Structure

```
humanmaximizer-lead-gen/
├── backend/
│   ├── agents/          # LangGraph nodes (research, qualification, sales)
│   ├── api/v1/          # FastAPI routes (search, leads, outreach, rag_query)
│   ├── models/          # SQLAlchemy ORM, TypedDicts, CRUD helpers
│   ├── prompts/         # Jinja2 templates (.j2)
│   ├── rag/             # ChromaDB ingestor + retriever
│   ├── tools/           # ContactFinder, Scraper, SerpSearch
│   ├── observability/   # Prometheus metrics + LangSmith tracing
│   ├── scripts/         # ingest.py
│   ├── tests/           # pytest suite
│   ├── alembic/         # Database migrations
│   ├── main.py          # FastAPI app factory
│   └── config.py        # Pydantic Settings
├── docker-compose.yml
├── .env.example
└── README.md
```
