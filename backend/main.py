import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, Response
from prometheus_client import make_asgi_app

from api import v1_router
from config import settings
from models import init_db
from observability import MetricsMiddleware, configure_tracing

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("HumanMaximizer Lead Gen API starting")
    logger.info(f"LLM model    : {settings.ollama_model}")
    logger.info(f"Chroma host  : {settings.chroma_host}:{settings.chroma_port}")
    logger.info(f"Database     : {settings.database_url}")

    os.makedirs("data", exist_ok=True)

    await init_db()
    logger.info("Database initialized")

    configure_tracing()

    yield

    logger.info("HumanMaximizer Lead Gen API shutting down")


_OPENAPI_TAGS = [
    {
        "name": "Lead Discovery",
        "description": (
            "Submit a keyword and location to run the full 3-agent pipeline "
            "(Research → Qualification → Sales). Use `max_leads` (1–10, default 5) to "
            "find multiple companies in one call — results are ranked by `qualification_score` "
            "so the highest-priority HRMS prospect is always first."
        ),
    },
    {
        "name": "Qualification",
        "description": (
            "Browse, filter, and inspect qualification results from previous pipeline runs. "
            "Every record includes full score breakdown (5 dimensions), confidence rating, "
            "LLM-generated reasoning, and data completeness. "
            "Sort by `score` to surface the highest-priority HRMS prospects."
        ),
    },
    {
        "name": "Outreach",
        "description": (
            "Regenerate personalised cold email and LinkedIn outreach for an existing lead "
            "using the latest RAG-indexed HumanMaximizer product knowledge. "
            "Use `POST /api/v1/rag/ingest` to refresh the knowledge base before regenerating."
        ),
    },
    {
        "name": "System",
        "description": (
            "Service health, runtime configuration, and RAG knowledge-base management. "
            "`POST /api/v1/rag/ingest` crawls humanmaximizer.com and refreshes ChromaDB. "
            "`GET /api/v1/rag/query` lets you inspect what chunks would be injected into outreach prompts."
        ),
    },
]

_SWAGGER_CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* ── Base / Body ─────────────────────────────────────────── */
body, .swagger-ui {
    background: #0a0e1a !important;
    font-family: 'Inter', system-ui, sans-serif !important;
    color: #c9d1d9 !important;
}
.swagger-ui .wrapper { max-width: 1100px; }

/* ── Topbar ──────────────────────────────────────────────── */
.swagger-ui .topbar {
    background: linear-gradient(90deg, #0a0e1a 0%, #0d1530 100%) !important;
    border-bottom: 1px solid rgba(0,212,255,0.2);
    padding: 14px 24px;
}
.swagger-ui .topbar .link span { display: none; }
.swagger-ui .topbar .link::before {
    content: "⬡ HumanMaximizer AI";
    color: #00d4ff;
    font-size: 18px;
    font-weight: 700;
    font-family: 'Inter', sans-serif;
    letter-spacing: 0.3px;
    text-shadow: 0 0 20px rgba(0,212,255,0.5);
}

/* ── Info block ──────────────────────────────────────────── */
.swagger-ui .info {
    background: linear-gradient(135deg, #0d1530 0%, #0a1628 100%);
    border: 1px solid rgba(0,212,255,0.15);
    border-radius: 12px;
    padding: 28px 32px;
    margin-bottom: 24px;
}
.swagger-ui .info .title {
    color: #ffffff !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 28px !important;
    font-weight: 700 !important;
    text-shadow: 0 0 30px rgba(0,212,255,0.3);
}
.swagger-ui .info .title small {
    background: rgba(0,212,255,0.15);
    color: #00d4ff;
    border: 1px solid rgba(0,212,255,0.3);
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 12px;
}
.swagger-ui .info p, .swagger-ui .info li, .swagger-ui .info td {
    color: #8b949e !important;
}
.swagger-ui .info a { color: #00d4ff !important; }
.swagger-ui .info .base-url { color: rgba(0,212,255,0.6) !important; font-size: 12px; }
.swagger-ui .info code {
    background: rgba(0,212,255,0.08) !important;
    color: #00d4ff !important;
    border-radius: 4px;
    padding: 1px 6px;
}

/* ── Tag headers ─────────────────────────────────────────── */
.swagger-ui .opblock-tag {
    color: #e6edf3 !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    border-bottom: 1px solid rgba(0,212,255,0.12) !important;
    padding: 12px 0 !important;
    letter-spacing: 0.2px;
}
.swagger-ui .opblock-tag:hover { background: rgba(0,212,255,0.04) !important; border-radius: 8px; }
.swagger-ui .opblock-tag-section { margin-bottom: 8px; }

/* ── Operation blocks ────────────────────────────────────── */
.swagger-ui .opblock {
    background: #0d1530 !important;
    border-radius: 10px !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    margin-bottom: 10px !important;
    transition: box-shadow 0.2s ease;
}
.swagger-ui .opblock:hover {
    box-shadow: 0 0 0 1px rgba(0,212,255,0.2), 0 4px 20px rgba(0,0,0,0.4) !important;
}
.swagger-ui .opblock.opblock-post {
    border-left: 3px solid #00d4ff !important;
    background: linear-gradient(90deg, rgba(0,212,255,0.04) 0%, #0d1530 40%) !important;
}
.swagger-ui .opblock.opblock-get {
    border-left: 3px solid #7c6af7 !important;
    background: linear-gradient(90deg, rgba(124,106,247,0.04) 0%, #0d1530 40%) !important;
}
.swagger-ui .opblock.opblock-post .opblock-summary-method {
    background: linear-gradient(135deg, #00b4d8, #00d4ff) !important;
    border-radius: 6px !important;
    font-weight: 700 !important;
    min-width: 70px;
    text-align: center;
    box-shadow: 0 0 12px rgba(0,212,255,0.3);
}
.swagger-ui .opblock.opblock-get .opblock-summary-method {
    background: linear-gradient(135deg, #6254e8, #7c6af7) !important;
    border-radius: 6px !important;
    font-weight: 700 !important;
    min-width: 70px;
    text-align: center;
    box-shadow: 0 0 12px rgba(124,106,247,0.3);
}
.swagger-ui .opblock-summary-description {
    color: #8b949e !important;
    font-size: 13px !important;
}
.swagger-ui .opblock-summary-path {
    color: #e6edf3 !important;
    font-family: 'Inter', monospace !important;
    font-size: 14px !important;
}

/* ── Expanded block body ─────────────────────────────────── */
.swagger-ui .opblock-body {
    background: #080c18 !important;
    border-top: 1px solid rgba(255,255,255,0.05) !important;
    border-radius: 0 0 10px 10px !important;
}
.swagger-ui .opblock-description-wrapper p,
.swagger-ui .opblock-external-docs-wrapper p,
.swagger-ui .opblock-title_normal p {
    color: #8b949e !important;
}
.swagger-ui .tab li { color: #8b949e !important; }
.swagger-ui .tab li.active { color: #00d4ff !important; border-bottom: 2px solid #00d4ff; }

/* ── Parameters & inputs ─────────────────────────────────── */
.swagger-ui .parameters-col_description p { color: #8b949e !important; }
.swagger-ui table thead tr td, .swagger-ui table thead tr th {
    color: #00d4ff !important;
    border-bottom: 1px solid rgba(0,212,255,0.15) !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.6px;
}
.swagger-ui .parameter__name { color: #e6edf3 !important; font-weight: 500 !important; }
.swagger-ui .parameter__type { color: #7c6af7 !important; font-size: 12px !important; }
.swagger-ui input[type=text], .swagger-ui textarea, .swagger-ui select {
    background: #0a0e1a !important;
    border: 1px solid rgba(0,212,255,0.2) !important;
    border-radius: 6px !important;
    color: #e6edf3 !important;
    font-family: 'Inter', sans-serif !important;
    padding: 8px 12px !important;
}
.swagger-ui input[type=text]:focus, .swagger-ui textarea:focus {
    border-color: #00d4ff !important;
    box-shadow: 0 0 0 2px rgba(0,212,255,0.15) !important;
    outline: none !important;
}

/* ── Execute button ──────────────────────────────────────── */
.swagger-ui .btn.execute {
    background: linear-gradient(135deg, #00b4d8, #00d4ff) !important;
    border: none !important;
    border-radius: 8px !important;
    color: #0a0e1a !important;
    font-weight: 700 !important;
    font-family: 'Inter', sans-serif !important;
    padding: 10px 24px !important;
    font-size: 13px !important;
    letter-spacing: 0.3px;
    box-shadow: 0 0 20px rgba(0,212,255,0.3) !important;
    transition: all 0.2s ease !important;
}
.swagger-ui .btn.execute:hover {
    box-shadow: 0 0 30px rgba(0,212,255,0.5) !important;
    transform: translateY(-1px);
}
.swagger-ui .btn.try-out__btn {
    background: transparent !important;
    border: 1px solid rgba(0,212,255,0.3) !important;
    color: #00d4ff !important;
    border-radius: 6px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 12px !important;
}
.swagger-ui .btn.try-out__btn:hover {
    background: rgba(0,212,255,0.08) !important;
}
.swagger-ui .btn.cancel {
    background: transparent !important;
    border: 1px solid rgba(255,80,80,0.3) !important;
    color: #ff5f57 !important;
    border-radius: 6px !important;
}

/* ── Response section ────────────────────────────────────── */
.swagger-ui .responses-inner { background: #080c18 !important; }
.swagger-ui .response-col_status { color: #00d4ff !important; font-weight: 600 !important; }
.swagger-ui .response-col_links { color: #7c6af7 !important; }
.swagger-ui .response code, .swagger-ui .microlight {
    background: #060a14 !important;
    color: #a8ff78 !important;
    border-radius: 6px !important;
    font-size: 13px !important;
    line-height: 1.6 !important;
}
.swagger-ui .highlight-code { background: #060a14 !important; border-radius: 8px !important; }

/* ── Curl / copy area ────────────────────────────────────── */
.swagger-ui .curl { background: #060a14 !important; color: #00d4ff !important; }
.swagger-ui .copy-to-clipboard {
    background: rgba(0,212,255,0.1) !important;
    border: 1px solid rgba(0,212,255,0.2) !important;
    border-radius: 4px !important;
}

/* ── Scrollbar ───────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0a0e1a; }
::-webkit-scrollbar-thumb { background: rgba(0,212,255,0.2); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(0,212,255,0.4); }

/* ── Models section — hide ───────────────────────────────── */
.swagger-ui section.models { display: none !important; }

/* ── Filter bar ──────────────────────────────────────────── */
.swagger-ui .filter-container input {
    background: #0d1530 !important;
    border: 1px solid rgba(0,212,255,0.2) !important;
    color: #e6edf3 !important;
    border-radius: 8px !important;
}

/* ── Schema / type badges ────────────────────────────────── */
.swagger-ui .model-box { background: #0d1530 !important; border-radius: 8px !important; }
.swagger-ui span.prop-type { color: #7c6af7 !important; }
.swagger-ui span.prop-format { color: #00d4ff !important; }
"""

app = FastAPI(
    title="HumanMaximizer Lead Generation Platform",
    description=(
        "AI-powered B2B lead discovery, qualification, and outreach generation "
        "for the **HumanMaximizer HRMS** product.\n\n"
        "## Quick start\n\n"
        "1. **`POST /api/v1/search`** — submit a keyword + location + `max_leads` (1–10); "
        "get multiple ranked leads with outreach copy in one call.\n"
        "2. **`GET /api/v1/leads`** — browse all leads sorted by qualification score.\n"
        "3. **`GET /api/v1/leads/{lead_id}`** — inspect score breakdown and reasoning for any lead.\n"
        "4. **`POST /api/v1/outreach/generate`** — regenerate outreach after refreshing the RAG index.\n"
        "5. **`POST /api/v1/rag/ingest`** — crawl humanmaximizer.com and refresh the ChromaDB knowledge base.\n\n"
        "## Qualification confidence\n\n"
        "Every lead carries a `qualification_confidence` score (0.0–1.0) that reflects "
        "both data completeness and score strength. Leads below **40 % data completeness** "
        "are never marked `is_qualified=true`, regardless of their raw score."
    ),
    version="1.0.0",
    contact={
        "name": "HumanMaximizer Platform Team",
        "email": "platform@humanmaximizer.com",
        "url": "https://humanmaximizer.com",
    },
    openapi_tags=_OPENAPI_TAGS,
    swagger_ui_parameters={
        "docExpansion": "list",
        "defaultModelsExpandDepth": -1,
        "displayRequestDuration": True,
        "filter": True,
        "tryItOutEnabled": True,
        "persistAuthorization": True,
    },
    docs_url=None,
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(MetricsMiddleware)

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

app.include_router(v1_router)


@app.get("/swagger-custom.css", include_in_schema=False)
async def swagger_custom_css():
    return Response(content=_SWAGGER_CUSTOM_CSS, media_type="text/css")


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui():
    """Branded Swagger UI with HumanMaximizer palette."""
    html = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} — API Reference",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        init_oauth=app.swagger_ui_init_oauth,
        swagger_ui_parameters=app.swagger_ui_parameters,
    )
    branded = html.body.decode("utf-8").replace(
        "<head>",
        '<head><meta name="color-scheme" content="dark">',
    ).replace(
        "</head>",
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link rel="stylesheet" href="/swagger-custom.css"></head>',
    )
    return HTMLResponse(content=branded)


@app.get("/health", tags=["System"], summary="Service health and runtime config")
async def health():
    return {
        "status": "ok",
        "service": "humanmaximizer-lead-gen",
        "version": "1.0.0",
        "llm_model": settings.ollama_model,
        "app_env": settings.app_env,
    }
