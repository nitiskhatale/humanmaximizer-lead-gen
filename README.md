# HumanMaximizer AI Lead Generation Platform

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-0.1.19-FF6B35)
![Mistral-7B](https://img.shields.io/badge/Mistral--7B-Q4__K__M-EE4C2C)
![ChromaDB](https://img.shields.io/badge/ChromaDB-0.5-FF6B00)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-Apache%202.0-blue)

> **Razor Infotech Pvt Ltd — AI Architect / GenAI Engineer Take-Home Assignment**

An autonomous AI platform that discovers, qualifies, and drafts personalised outreach for B2B HRMS prospects — powered by a 3-agent LangGraph pipeline, RAG-grounded generation, and local Mistral-7B inference via Ollama.

---

## Demo

| | Link |
|---|---|
| **Architecture Walkthrough** | [Watch on Loom](https://www.loom.com/share/e1174aaa6f19458dbe18322e1020506e) |
| **Live Demo** | [Watch on Loom](https://www.loom.com/share/6095566035ef43788ea62e3c5072a753) |

---

## Table of Contents

1. [Demo](#demo)
2. [Business Use Case](#1-business-use-case)
2. [Multi-Agent Architecture](#2-multi-agent-architecture)
3. [RAG Pipeline](#3-rag-pipeline)
4. [Open Source LLM Strategy](#4-open-source-llm-strategy)
5. [Fine-Tuning Strategy](#5-fine-tuning-strategy)
6. [Architecture Document (PDF)](#6-architecture-document-pdf)
7. [Observability & Monitoring](#7-observability--monitoring)
8. [Quickstart](#8-quickstart)
9. [Streamlit Demo UI](#9-streamlit-demo-ui)
10. [Prompt Examples](#10-prompt-examples)
11. [Project Structure](#11-project-structure)
12. [Running Tests](#12-running-tests)
13. [Environment Variables](#13-environment-variables)

---

## 1. Business Use Case

**HumanMaximizer** is an enterprise HRMS platform for Indian businesses — covering payroll, attendance, compliance (ESIC, PF, PT, CLRA), recruitment, and workforce management.

**The problem:** The sales team manually searches for prospects via Google, qualifies them in spreadsheets, and hand-writes outreach — a process that is slow, inconsistent, and doesn't scale.

**The solution:** This AI platform replaces that manual process with a fully autonomous pipeline:

| Stage | What It Does |
|---|---|
| **Discover** | Searches Google (SerpAPI) for companies matching a keyword + location |
| **Research** | Scrapes company websites, extracts employee count, industry, tech stack, HR decision makers |
| **Qualify** | Scores each prospect 0–100 across 5 HRMS-fit dimensions with deterministic rules |
| **Generate** | Writes RAG-grounded cold email + LinkedIn message personalised to each company |
| **Rank** | Returns all leads sorted by `qualification_score` — highest-value prospect first |

**Example:** `POST /api/v1/search {"keyword": "manufacturing companies", "location": "Pune, India", "max_leads": 5}` returns 5 ranked companies with complete research, score breakdowns, and ready-to-send outreach in one API call.

---

## 2. Multi-Agent Architecture

The pipeline uses **LangGraph StateGraph** — a stateful directed acyclic graph with a conditional routing edge that deterministically routes qualified leads to the Sales Agent and discards disqualified ones.

```
POST /api/v1/search
         │
         ▼
  ┌──────────────────────────────────────────────────┐
  │           LangGraph StateGraph (LeadState)        │
  │                                                   │
  │  ┌─────────────┐   ┌──────────────────┐           │
  │  │ ResearchAgent│──►│QualificationAgent│           │
  │  │             │   │                  │           │
  │  │ SerpAPI     │   │  5-dim scoring   │           │
  │  │ Web scrape  │   │  0–100 total     │           │
  │  │ DM extract  │   │  LLM reasoning   │           │
  │  │ LLM summary │   │                  │           │
  │  └─────────────┘   └────────┬─────────┘           │
  │                             │                     │
  │                   score≥35  │  score<35            │
  │                             ▼       ▼              │
  │                    ┌────────────┐  END             │
  │                    │ SalesAgent │  (disqualified)  │
  │                    │            │                  │
  │                    │ RAG query  │                  │
  │                    │ Cold email │                  │
  │                    │ LinkedIn   │                  │
  │                    └────────────┘                  │
  └──────────────────────────────────────────────────┘
         │
         ▼
     SQLite DB  +  JSON response
```

### Agent Responsibilities

#### Agent 1: ResearchAgent (`backend/agents/research_agent.py`)

**Input:** `keyword`, `location`

**Process:**
1. `SerpSearchTool` — calls SerpAPI with `gl=in, hl=en` for India-localised results
2. `ScraperTool` — fetches top result URL via httpx + BeautifulSoup
3. `ContactFinderTool` — regex pattern matching for 18 HRMS decision-maker titles
4. Mistral-7B via `research_summary.j2` — generates 3-paragraph structured summary

**Output written to LeadState:** `company_name`, `domain`, `employee_count`, `industry`, `hq_location`, `tech_stack`, `decision_makers`, `growth_signal`, `raw_summary`

#### Agent 2: QualificationAgent (`backend/agents/qualification_agent.py`)

**Input:** Enriched LeadState from ResearchAgent

**Process:**
1. `score_company_size()` — 0–20 based on employee brackets
2. `score_industry()` — 0–20 (primary=20, adjacent=12, unknown=6, other=4)
3. `score_tech_stack()` — 0–20 (spreadsheet=18, legacy HRMS=12, unknown=10, modern HRMS=4)
4. `score_dm_reachability()` — 0–20 confidence-weighted by contact completeness
5. `score_growth_signal()` — 0–20 (hiring/funding/expansion=20, stable=10, contracting=2)
6. Completeness gate: < 40% data completeness → disqualified regardless of score
7. Mistral-7B via `qualification_reasoning.j2` — 2-sentence reasoning

**Output:** `qualification_score` (0–100), `score_breakdown`, `is_qualified`, `qualification_reasoning`, `qualification_confidence`

**Conditional edge:** `score ≥ 35 → SalesAgent` | `score < 35 → END (disqualified)`

#### Agent 3: SalesAgent (`backend/agents/sales_agent.py`)

**Input:** Qualified LeadState

**Process:**
1. Builds RAG query from company profile + industry + growth signal
2. `nomic-embed-text` embeds query → ChromaDB cosine search → top-5 product chunks
3. Mistral-7B via `cold_email.j2` — 150–220 word cold email with SUBJECT/BODY format
4. Mistral-7B via `linkedin_message.j2` — ≤300 char LinkedIn connection request
5. `SelfCritiqueTool` — second LLM pass verifies claims against RAG chunks

**Output:** `outreach_email`, `linkedin_message`, `rag_context_used` (full audit trail)

### Why LangGraph over CrewAI / AutoGen

| Framework | Why |
|---|---|
| **LangGraph** (selected) | Explicit state machine — edges are code, not LLM decisions. Conditional edge enforces deterministic routing. Full observability of state at every step. |
| CrewAI | Hides agent-to-agent calls behind abstractions. Hard to debug. LLM decides routing — unpredictable in production. |
| AutoGen | Designed for conversational multi-agent loops, not structured data pipelines. Overkill for deterministic lead scoring. |

---

## 3. RAG Pipeline

All outreach is **grounded in real HumanMaximizer product knowledge** crawled from humanmaximizer.com and indexed in ChromaDB. This prevents hallucinated product claims.

### Ingestion Pipeline

```
humanmaximizer.com
       │
       ▼
WebIngestor (backend/rag/ingestor.py)
  ├── Async HTTP crawler (httpx)  · depth=3 · max 30 pages
  ├── BeautifulSoup HTML parser   · strips script/style/nav/footer
  └── Minimum 200 chars per page
       │
       ▼
RecursiveCharacterTextSplitter
  ├── chunk_size=512 tokens
  ├── chunk_overlap=64 tokens
  └── separators: \n\n → \n → ". " → " "
       │
       ▼
OllamaEmbeddings (nomic-embed-text)
  ├── 768-dimensional vectors
  └── FP16 · ~270 MB VRAM
       │
       ▼
ChromaDB PersistentClient
  ├── Collection: humanmaximizer_knowledge
  ├── Metric: hnsw:cosine
  └── Idempotent upsert by MD5 chunk ID
```

### Retrieval at Query Time

```python
# Each lead triggers:
rag_query = f"HRMS features for {industry} company [{raw_summary[:200]}]"
chunks = retriever.retrieve(rag_query, k=5)  # cosine similarity, top-5
# Chunks injected into cold_email.j2 prompt
```

### Hallucination Prevention — 3 Layers

| Layer | Mechanism | Type |
|---|---|---|
| **Layer 1** | `cold_email.j2` explicitly instructs: *"Use ONLY the facts below. Do not invent statistics."* | Synchronous |
| **Layer 2** | `rag_context_used` stored verbatim on every lead — full audit trail of what grounded each email | Synchronous |
| **Layer 3** | `SelfCritiqueTool` makes a second Mistral-7B pass comparing email claims to RAG chunks; emits `hallucination_checks_total` Prometheus counter | Instrumented |

---

## 4. Open Source LLM Strategy

Full documentation: [`docs/llm_strategy.md`](docs/llm_strategy.md)

### Model Selected: Mistral-7B-Instruct-v0.3

| Model | Params | Context | License | VRAM Q4 | Decision |
|---|---|---|---|---|---|
| **Mistral-7B-Instruct-v0.3** | 7B | 8k | Apache 2.0 | ~4.4 GB | **Selected** |
| Llama-3-8B-Instruct | 8B | 8k | Meta Llama 3 | ~5.0 GB | Not selected — Meta license; slightly larger footprint |
| Phi-3-Mini-4k-Instruct | 3.8B | 4k | MIT | ~2.3 GB | Not selected — 4k context too short for RAG+company profile |
| Gemma-7B-Instruct | 7B | 8k | Gemma ToU | ~4.4 GB | Not selected — restrictive commercial license |

**Why Mistral-7B:**
1. **Instruction-following quality** — reliably produces structured `SUBJECT:/BODY:` email format and 2-sentence reasoning
2. **Indian-English domain fit** — strong coverage of business English, Indian company names, compliance terms (ESIC, PF, CLRA, PT)
3. **8k context window** — fits 5 RAG chunks (~2,500 tokens) + company profile (~800) + prompt (~400)
4. **Apache 2.0 license** — fully commercial-friendly, no usage restrictions
5. **Single model for 3 agents** — one Ollama instance serves all agents, simplifying deployment

### Quantization: Q4_K_M (GGUF via Ollama/llama.cpp)

| Format | VRAM (7B) | Quality vs FP16 | Notes |
|---|---|---|---|
| FP16 | ~14 GB | 100% | Requires A100/H100 |
| Q8_0 | ~7.7 GB | ~99% | Exceeds 8 GB GPU limit |
| **Q4_K_M** | **~4.4 GB** | **~97%** | **Selected** |
| Q4_K_S | ~4.1 GB | ~96% | Slightly worse structured output |
| Q3_K_M | ~3.3 GB | ~93% | Measurable JSON corruption |

**Q4_K_M decoded:**
- **Q4** — 4-bit integer weights (75% VRAM reduction vs FP16)
- **K** — K-quants mixed precision per tensor; attention heads retain more bits than feed-forward
- **M** — Medium variant, balanced quality vs size

### GPU Requirements

| Target | GPU | VRAM | Tokens/sec | Notes |
|---|---|---|---|---|
| Development | RTX 3070 / RTX 4060 Ti | 8 GB | ~40–60 | Q4_K_M + nomic-embed-text fit simultaneously |
| Production | RTX 4090 / A10G | 24 GB | ~80–120 | Run Q8_0; higher concurrency |
| Cloud (budget) | T4 (Colab/GCP) | 16 GB | ~50–70 | Handles Q4_K_M comfortably |
| CPU fallback | Any | — | ~5–15 | Set `OLLAMA_NUM_GPU=0`; ~60–120s per lead |

---

## 5. Fine-Tuning Strategy

Full documentation: [`docs/fine_tuning_strategy.md`](docs/fine_tuning_strategy.md)

### When Fine-Tuning > Prompting

| Scenario | Prompting + RAG | Fine-Tuning |
|---|---|---|
| New product features | Re-ingest website — no retraining | Full retraining cycle |
| Output format consistency | Jinja2 enforces structure | Bakes format into weights |
| Indian compliance terms | Inject via RAG chunks | Learned during training |
| Cold start (no data) | Works immediately | Needs 300–500 examples |

**Trigger points for fine-tuning:**
1. LLM consistently produces malformed `SUBJECT:/BODY:` splits
2. Qualification reasoning hallucinates compliance regulation names not in RAG
3. Cold emails revert to generic placeholder language despite specific RAG chunks

### Approach: QLoRA with Unsloth

**Why QLoRA:** Full fine-tuning of 7B parameters requires ~80–120 GB VRAM. QLoRA trains low-rank adapter matrices on top of a 4-bit base — requires only ~8–12 GB VRAM on a single consumer GPU.

**Why Unsloth:** 2–3× faster QLoRA training vs HuggingFace PEFT via custom Triton CUDA kernels + Flash Attention 2.

```python
from unsloth import FastLanguageModel

model, tokenizer = FastLanguageModel.from_pretrained(
    "mistralai/Mistral-7B-Instruct-v0.3",
    max_seq_length=4096,
    load_in_4bit=True,
)
model = FastLanguageModel.get_peft_model(
    model,
    r=16,                    # LoRA rank
    lora_alpha=32,           # scaling factor
    lora_dropout=0.05,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
    use_gradient_checkpointing="unsloth",
)
```

### Dataset Format (Alpaca JSONL)

```jsonl
{
  "instruction": "Write a personalised B2B cold email for an HRMS sale.",
  "input": "Company: Bharat Forge (Manufacturing, 10,000 employees, SAP HR). DM: Rajesh Kumar, VP HR. RAG: HumanMaximizer automates multi-plant payroll, CLRA filings.",
  "output": "SUBJECT: Modernise Multi-Plant HR at Bharat Forge\n\nBODY:\nDear Rajesh,\n\nBharat Forge's expansion into EV adds plants and compliance complexity under CLRA. HumanMaximizer consolidates payroll across all plants into one dashboard.\n\nCould we schedule 15 minutes Thursday?\n\nBest regards,\nHumanMaximizer Sales Team"
}
```

**Dataset construction:** Run pipeline on 200–300 companies → human sales expert reviews → approved outputs become training data → 300–500 examples (quality > quantity)

**Post-training deployment:** LoRA adapter → merge into base → GGUF Q4_K_M → Ollama (drop-in, zero API changes)

---

## 6. Architecture Document (PDF)

Generate all PDF deliverables with one command:

```bash
# From project root
python scripts/generate_architecture_pdf.py

# Outputs:
#   docs/architecture.pdf          — System architecture, agent flow, RAG, scaling, monitoring
#   docs/fine_tuning_strategy.pdf  — QLoRA, dataset format, training config, evaluation
#   docs/llm_strategy.pdf          — Model selection, quantization, GPU requirements
```

**Contents of `docs/architecture.pdf`:**
- System architecture diagram (Mermaid)
- Agent orchestration flow with data flow at each step
- RAG pipeline (ingestion → chunking → embedding → retrieval)
- LLM model selection rationale and quantization strategy
- Scaling approach (vertical + horizontal)
- Observability and monitoring with alert thresholds

---

## 7. Observability & Monitoring

Full documentation in [`docs/architecture.md`](docs/architecture.md) — Observability section.

### Prometheus Metrics (`GET /metrics`)

| Metric | Type | What It Measures | Alert Condition |
|---|---|---|---|
| `leads_processed_total` | Counter | Pipeline throughput by `status` | Drop > 50% vs 5-min baseline |
| `lead_pipeline_stage_seconds` | Histogram | Per-endpoint latency | p99 > 30s on `/api/v1/search` |
| `lead_qualification_score` | Histogram | Score distribution 0–100 | Mean drops below 30 |
| `rag_chunks_retrieved` | Histogram | ChromaDB retrieval count | p50 = 0 (ChromaDB down/empty) |
| `hallucination_checks_total` | Counter | Self-critique results (`is_grounded`) | `is_grounded=false` rate > 10% in 15 min |
| `llm_calls_total` | Counter | LLM calls per agent | Error rate > 5% |

### Hallucination Monitoring

Three-layer system prevents and detects hallucinations:

1. **Prompt constraint** — Jinja2 templates forbid invented facts: `"Use ONLY the facts below"`
2. **RAG citation trail** — `rag_context_used` on every lead enables manual audit of any email claim
3. **Automated self-critique** — `SelfCritiqueTool` runs a second Mistral-7B pass; emits `hallucination_checks_total{is_grounded=false}` counter

### Latency Monitoring

`MetricsMiddleware` records `lead_pipeline_stage_seconds` histogram on every HTTP request. Buckets: `[0.5, 1, 2, 5, 10, 30, 60, 120]` seconds. Tracks p50/p95/p99 per API path.

### Agent Failure Monitoring

- Every agent node wraps execution in `try/except`; exceptions append to `LeadState.errors`
- `errors` list persisted to DB and returned in every API response
- LangSmith traces all LangGraph nodes when `LANGCHAIN_API_KEY` is set — failed nodes appear as error spans with full stack traces

### Lead Quality Metrics

`lead_qualification_score` histogram samples every pipeline run. Combined with `leads_processed_total{status=disqualified}` rate — detects keyword drift where irrelevant queries produce low-quality leads.

---

## 8. Quickstart

**Prerequisites:** Docker with NVIDIA Container Toolkit (or CPU fallback)

```bash
# 1. Clone the repository
git clone https://github.com/nitiskhatale/humanmaximizer-lead-gen.git
cd humanmaximizer-lead-gen

# 2. Configure environment
cp .env.example .env
# Edit .env and set SERPAPI_KEY for live search (optional — system works without it)

# 3. Start all services (Ollama + ChromaDB + FastAPI)
docker compose up -d

# 4. Pull LLM and embedding model (one-time, ~4.4 GB)
docker compose exec ollama ollama pull mistral:7b-instruct-v0.3-q4_K_M
docker compose exec ollama ollama pull nomic-embed-text

# 5. Ingest HumanMaximizer product knowledge into ChromaDB
docker compose exec api python scripts/ingest.py

# 6. Open the API
open http://localhost:8000/docs        # Swagger UI (branded)
```

> **CPU-only mode:** Remove the `deploy.resources.reservations.devices` block in `docker-compose.yml` before step 3. Inference will be ~10× slower (~60–120s per lead) but fully functional.

### API Demo (4 steps in Swagger UI)

**Step 1 — Run the pipeline (multi-company, ranked)**
```json
POST /api/v1/search
{
  "keyword": "manufacturing companies",
  "location": "Pune, India",
  "max_leads": 5
}
```
Returns 5 leads ranked by `qualification_score` descending. First entry is the best HRMS prospect.

**Step 2 — Inspect full lead details**
```
GET /api/v1/leads/{lead_id}
```
Shows score breakdown, DM contacts, qualification reasoning, and confidence.

**Step 3 — Generate RAG-grounded outreach**
```json
POST /api/v1/outreach/generate
{"lead_id": "<id from step 1>"}
```
Returns `outreach_email.subject`, `outreach_email.body`, `linkedin_message`, and `rag_context_used`.

**Step 4 — Debug ChromaDB retrieval**
```
GET /api/v1/rag/query?q=payroll+compliance+manufacturing
```
Returns raw chunks that would be injected into the outreach prompt.

---

## 9. Streamlit Demo UI

A full-featured Streamlit dashboard is included for demo and evaluation purposes.

```bash
# Install Streamlit dependencies
pip install -r requirements-streamlit.txt

# Start the FastAPI backend first (see Quickstart)
# Then launch the UI:
streamlit run streamlit_app.py
# Opens at: http://localhost:8501
```

**Pages:**
- **Home** — Business use case, 3-agent pipeline overview, live system stats
- **Find Leads** — Live lead search with chain-of-thought agent trace + ranked results
- **Lead History** — Browse all leads with score distribution histogram and full detail view
- **Knowledge Base** — Manage and test RAG ingestion from humanmaximizer.com

---

## 10. Prompt Examples

All prompts are Jinja2 templates in `backend/prompts/`. See [`docs/prompt_examples.md`](docs/prompt_examples.md) for full examples.

### ResearchAgent — `research_summary.j2`

**Input context:**
```
Company: Bharat Forge Ltd
Domain: bharatforge.com
Industry: Manufacturing
Employees: 10,000
Location: Pune, Maharashtra
Current HR Tech: SAP HR, Oracle HRMS
Growth Signal: Hiring surge (EV expansion)
```

**LLM output (Mistral-7B):**
```
COMPANY OVERVIEW: Bharat Forge is one of India's largest auto-component manufacturers with
10,000 employees across multiple plants in Pune and Aurangabad...

HR PAIN POINTS: With 10,000 employees across plants, Bharat Forge faces multi-site payroll
complexity, contract-labour compliance under CLRA, and high-volume attendance management...

HRMS FIT SIGNAL: Strong candidate — large manufacturing workforce with a legacy SAP HR
system that is expensive to maintain. The EV expansion adds compliance and workforce
complexity that a modern HRMS can address efficiently...
```

### QualificationAgent — Score breakdown example

```
Bharat Forge Ltd — Score: 88/100
  Company Size Fit:             20/20  (> 2,000 employees)
  Industry Relevance:           20/20  (Manufacturing — primary target)
  Tech Stack Gap:               12/20  (Legacy SAP HR — replacement candidate)
  Decision Maker Reachability:  16/20  (VP HR found with email + LinkedIn)
  Growth Signal:                20/20  (Hiring surge — EV segment expansion)

Qualification Reasoning:
  "Bharat Forge's legacy SAP HR across multiple plants (12/20 tech gap) combined with
  active EV expansion (20/20 growth signal) makes this the highest-priority prospect.
  The primary constraint is limited reachability — only one DM identified with confirmed
  email; LinkedIn outreach should run in parallel."
```

### SalesAgent — Cold email output

```
SUBJECT: Streamline Multi-Plant HR Compliance at Bharat Forge

BODY:
Dear Rajesh,

Bharat Forge's expansion into the EV segment means adding plants, headcount, and
cross-state compliance obligations — exactly the scenario where multi-site payroll
under CLRA and PT becomes costly to manage in SAP HR.

HumanMaximizer consolidates payroll across all plants into a single dashboard, automates
statutory filings (CLRA, PF, ESIC, PT), and gives real-time compliance visibility — without
replacing your existing ERP.

We've helped similar large manufacturers cut payroll processing time by over 60% by
centralising multi-location attendance and leave data.

Would you have 15 minutes this Thursday for a demo tailored for large-scale manufacturers?

Best regards,
HumanMaximizer Sales Team
```

### SalesAgent — LinkedIn message

```
Hi Rajesh, scaling Bharat Forge across EV plants while managing CLRA compliance in
SAP HR must be creating real cost and risk. HumanMaximizer automates statutory filings
across all plants from one dashboard. Would you be open to a quick chat?
```

---

## 11. Project Structure

```
humanmaximizer-lead-gen/
├── backend/
│   ├── agents/
│   │   ├── graph.py                    # LangGraph StateGraph definition
│   │   ├── research_agent.py           # Agent 1: search + scrape + summarise
│   │   ├── qualification_agent.py      # Agent 2: 5-dim scoring + reasoning
│   │   └── sales_agent.py              # Agent 3: RAG retrieval + outreach
│   ├── api/v1/
│   │   ├── search.py                   # POST /api/v1/search
│   │   ├── leads.py                    # GET /api/v1/leads, /leads/{id}
│   │   ├── outreach.py                 # POST /api/v1/outreach/generate
│   │   ├── rag_query.py                # GET /api/v1/rag/query
│   │   └── rag_ingest.py               # POST /api/v1/rag/ingest
│   ├── models/
│   │   ├── state.py                    # LeadState TypedDict
│   │   ├── lead.py                     # SQLAlchemy ORM model
│   │   ├── crud.py                     # Async DB operations
│   │   └── database.py                 # SQLAlchemy async engine setup
│   ├── prompts/
│   │   ├── research_summary.j2         # Agent 1 prompt template
│   │   ├── qualification_reasoning.j2  # Agent 2 prompt template
│   │   ├── cold_email.j2               # Agent 3 email prompt
│   │   ├── linkedin_message.j2         # Agent 3 LinkedIn prompt
│   │   └── self_critique.j2            # Hallucination detection prompt
│   ├── rag/
│   │   ├── ingestor.py                 # WebIngestor + chunking + embedding
│   │   └── retriever.py                # ChromaDB cosine retrieval
│   ├── tools/
│   │   ├── serp_search.py              # SerpAPI Google search
│   │   ├── scraper.py                  # httpx + BeautifulSoup web scraper
│   │   ├── contact_finder.py           # Regex DM title/email extractor
│   │   └── self_critique_tool.py       # Hallucination verification
│   ├── observability/
│   │   ├── metrics.py                  # Prometheus counters + histograms
│   │   ├── middleware.py               # HTTP metrics middleware
│   │   └── langsmith.py                # LangSmith tracing configuration
│   ├── alembic/                        # Database migrations
│   ├── tests/                          # pytest test suite (82 tests)
│   ├── scripts/ingest.py               # One-time RAG ingestion CLI
│   ├── main.py                         # FastAPI app factory + Swagger branding
│   └── config.py                       # Pydantic Settings
├── docs/
│   ├── architecture.md                 # Full architecture document (Mermaid + tables)
│   ├── architecture.pdf                # Generated PDF deliverable
│   ├── fine_tuning_strategy.md         # QLoRA/Unsloth fine-tuning guide
│   ├── fine_tuning_strategy.pdf        # Generated PDF deliverable
│   ├── llm_strategy.md                 # Model selection + quantization analysis
│   ├── llm_strategy.pdf                # Generated PDF deliverable
│   └── prompt_examples.md              # All 5 prompt templates with examples
├── notebooks/
│   └── rag_evaluation.ipynb            # ChromaDB retrieval quality evaluation
├── scripts/
│   └── generate_architecture_pdf.py    # ReportLab PDF generator for docs/
├── streamlit_app.py                    # Streamlit demo dashboard
├── requirements-streamlit.txt          # Streamlit dependencies
├── docker-compose.yml                  # Ollama + ChromaDB + FastAPI services
├── .env.example                        # Environment variable template
├── Makefile                            # make up/down/test/pdf/ingest
├── pyproject.toml                      # Python project config
└── FINAL_IMPLEMENTATION.md             # Detailed technical implementation notes
```

---

## 12. Running Tests

```bash
cd backend
pytest tests/ -v

# Expected: 82 passed
```

Tests are fully isolated — no Ollama, no ChromaDB, no network required:
- `tests/test_qualification.py` — 34 unit tests for all 5 deterministic scoring functions
- `tests/test_tools.py` — 9 unit tests for ContactFinder and ScraperTool
- `tests/test_api.py` — API integration tests using in-memory SQLite

---

## 13. Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server endpoint |
| `OLLAMA_MODEL` | `mistral:7b-instruct-v0.3-q4_K_M` | LLM model tag |
| `OLLAMA_NUM_GPU` | `1` | GPU layers for Ollama (set `0` for CPU-only) |
| `CHROMA_HOST` | `localhost` | ChromaDB host |
| `CHROMA_PORT` | `8001` | ChromaDB port |
| `CHROMA_COLLECTION` | `humanmaximizer_knowledge` | ChromaDB collection name |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/leads.db` | Async DB connection string |
| `SERPAPI_KEY` | _(empty)_ | SerpAPI key for live Google search |
| `LANGCHAIN_API_KEY` | _(empty)_ | LangSmith tracing (optional) |
| `APP_ENV` | `development` | `development` or `production` |
| `LOG_LEVEL` | `INFO` | Python logging level |

> **Production upgrade:** Change `DATABASE_URL` to `postgresql+asyncpg://...` — zero code changes required.

---

## Deliverables

| Deliverable | Location | Status |
|---|---|---|
| GitHub Repository | This repository | ✅ |
| README | `README.md` | ✅ |
| Architecture PDF | `docs/architecture.pdf` (`make pdf`) | ✅ |
| Fine-Tuning Strategy PDF | `docs/fine_tuning_strategy.pdf` | ✅ |
| LLM Strategy PDF | `docs/llm_strategy.pdf` | ✅ |
| Prompt Examples | `docs/prompt_examples.md` + `backend/prompts/*.j2` | ✅ |
| Fine-Tuning Strategy Explanation | `docs/fine_tuning_strategy.md` | ✅ |
| Demo Video | 5–10 min screen recording (see `docs/demo_video_script.md`) | 📹 |

---

Built for Razor Infotech Pvt Ltd · LangGraph · Mistral-7B · ChromaDB · FastAPI · Prometheus
