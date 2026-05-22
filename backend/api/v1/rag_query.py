"""
GET /api/v1/rag/query?q=... — debug endpoint to inspect ChromaDB retrieval.

Shows exactly what chunks the SalesAgent would receive for a given query.
Useful during the demo to show RAG is working before calling /outreach/generate.
"""
import logging

from fastapi import APIRouter, Query

from rag.retriever import build_retriever, retrieve_chunks

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/query",
    summary="Retrieve RAG chunks from ChromaDB",
    description=(
        "Runs cosine similarity retrieval against the ChromaDB collection and returns the "
        "top-5 chunks that would be injected into the outreach prompts. "
        "Run `scripts/ingest.py` first to populate the index."
    ),
    tags=["System"],
)
async def rag_query(
    q: str = Query(
        ...,
        description="Retrieval query (e.g. 'payroll compliance manufacturing')",
        examples=["payroll compliance manufacturing 500 employees"],
    ),
):
    retriever = build_retriever()
    if retriever is None:
        return {
            "query": q,
            "chunks": [],
            "message": "ChromaDB collection not found. Run: docker compose exec api python scripts/ingest.py",
        }

    chunks = retrieve_chunks(q, retriever)
    return {
        "query": q,
        "chunks_count": len(chunks),
        "chunks": chunks,
    }
