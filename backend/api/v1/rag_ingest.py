"""
POST /api/v1/rag/ingest — trigger RAG ingestion from the API.

Crawls humanmaximizer.com, chunks content, embeds with nomic-embed-text,
and upserts into ChromaDB. Runs in a thread pool to avoid blocking
the async event loop (WebIngestor.run() calls asyncio.run() internally).
"""
import asyncio
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class IngestRequest(BaseModel):
    refresh: bool = False


@router.post(
    "/ingest",
    summary="Ingest / refresh HumanMaximizer knowledge base",
    description=(
        "Crawls `humanmaximizer.com` (up to 30 pages, depth 3), chunks content into 512-token "
        "segments with 64-token overlap, embeds with `nomic-embed-text`, and upserts into "
        "ChromaDB.\n\n"
        "Set `refresh=true` to wipe the existing collection before re-indexing. "
        "The operation runs in a background thread and may take 1–3 minutes depending on "
        "Ollama embedding latency."
    ),
    tags=["System"],
)
async def ingest_knowledge(request: IngestRequest):
    from rag.ingestor import WebIngestor

    ingestor = WebIngestor()
    loop = asyncio.get_running_loop()
    try:
        count: int = await loop.run_in_executor(
            None, lambda: ingestor.run(request.refresh)
        )
        return {
            "status": "ok",
            "chunks_indexed": count,
            "refresh": request.refresh,
            "message": f"Indexed {count} chunks from humanmaximizer.com into ChromaDB.",
        }
    except Exception as exc:
        logger.error("RAG ingest failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
