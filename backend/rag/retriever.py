"""
Retriever factory — queries ChromaDB collection directly via native client.

Returns None gracefully if the collection has not yet been ingested,
so the API stays runnable before scripts/ingest.py has been executed.
Uses native chromadb client + OllamaEmbeddings to avoid langchain-chroma
_type metadata incompatibility with chromadb 0.6.x.
"""
import logging

import chromadb
from langchain_ollama import OllamaEmbeddings

from config import settings

logger = logging.getLogger(__name__)


def build_retriever():
    """
    Connect to ChromaDB and return the collection handle.

    Returns None if the collection does not exist yet (pre-ingestion).
    """
    try:
        import os
        persist_path = os.path.abspath(settings.chroma_persist_dir)
        if not os.path.exists(persist_path):
            logger.warning(
                "ChromaDB persist dir '%s' not found. Run scripts/ingest.py first.",
                persist_path,
            )
            return None

        client = chromadb.PersistentClient(path=persist_path)
        try:
            collection = client.get_collection(name=settings.chroma_collection)
        except Exception:
            logger.warning(
                "ChromaDB collection '%s' not found. Run scripts/ingest.py first.",
                settings.chroma_collection,
            )
            return None
        logger.info(
            "ChromaDB collection ready (collection='%s', count=%d)",
            settings.chroma_collection,
            collection.count(),
        )
        return collection

    except Exception as exc:
        logger.warning("Could not connect to ChromaDB: %s", exc)
        return None


def retrieve_chunks(query: str, retriever=None) -> list[str]:
    """
    Embed the query and run similarity search against ChromaDB collection.

    Args:
        query: natural-language retrieval query
        retriever: chromadb Collection from build_retriever(); None → empty list

    Returns:
        List of up to 5 chunk text strings for injection into prompts.
    """
    if retriever is None:
        return []
    try:
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        query_embedding = embeddings.embed_query(query)
        results = retriever.query(
            query_embeddings=[query_embedding],
            n_results=min(5, retriever.count()),
            include=["documents"],
        )
        docs = results.get("documents", [[]])[0]
        return [d for d in docs if d]
    except Exception as exc:
        logger.warning("Retrieval failed: %s", exc)
        return []
