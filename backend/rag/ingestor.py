"""
WebIngestor — crawls humanmaximizer.com, chunks content, embeds using
nomic-embed-text via Ollama, and upserts into ChromaDB.

Run once:   python scripts/ingest.py
Refresh:    python scripts/ingest.py --refresh
"""
import hashlib
import logging
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import chromadb
import httpx
from bs4 import BeautifulSoup
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings

from config import settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.humanmaximizer.com"
_MAX_DEPTH = 3
_MAX_PAGES = 30
_CHUNK_SIZE = 512
_CHUNK_OVERLAP = 64
_HEADERS = {"User-Agent": "HumanMaximizer-RAG-Ingestor/1.0"}
_SKIP_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".zip", ".exe"}


class WebIngestor:
    def __init__(self) -> None:
        self._embeddings = OllamaEmbeddings(
            model="nomic-embed-text",
        )
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=_CHUNK_SIZE,
            chunk_overlap=_CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " "],
        )

    def run(self, refresh: bool = False) -> int:
        """Crawl, chunk, embed, upsert. Returns number of chunks indexed."""
        import asyncio
        logger.info("Starting ingestion from %s (refresh=%s)", _BASE_URL, refresh)

        pages = asyncio.run(self._crawl(_BASE_URL))
        logger.info("Crawled %d pages", len(pages))

        chunks = self._chunk(pages)
        logger.info("Generated %d chunks", len(chunks))

        count = self._upsert(chunks, refresh=refresh)
        logger.info("Upserted %d chunks into collection '%s'", count, settings.chroma_collection)
        return count

    async def _crawl(self, base_url: str) -> list[dict]:
        visited: set[str] = set()
        pages: list[dict] = []

        async def _fetch(url: str, depth: int) -> None:
            if depth > _MAX_DEPTH or url in visited or len(pages) >= _MAX_PAGES:
                return
            visited.add(url)
            lower = url.lower()
            if any(lower.endswith(ext) for ext in _SKIP_EXTENSIONS):
                return
            try:
                async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                    r = await client.get(url, headers=_HEADERS)
                    if "text/html" not in r.headers.get("content-type", ""):
                        return
                    soup = BeautifulSoup(r.text, "html.parser")
                    for tag in soup(["script", "style", "nav", "footer", "header"]):
                        tag.decompose()
                    title = soup.title.string.strip() if soup.title else url
                    text = soup.get_text(separator="\n", strip=True)
                    if len(text) > 200:
                        pages.append({"url": url, "title": title, "text": text})
                        logger.info("  [depth=%d] %s (%d chars)", depth, url, len(text))
                    for a in soup.find_all("a", href=True):
                        href = urljoin(url, a["href"])
                        if urlparse(href).netloc == urlparse(base_url).netloc:
                            await _fetch(href, depth + 1)
            except Exception as exc:
                logger.warning("  skip %s: %s", url, exc)

        await _fetch(base_url, 0)
        return pages

    def _chunk(self, pages: list[dict]) -> list[dict]:
        chunks = []
        for page in pages:
            for i, chunk_text in enumerate(self._splitter.split_text(page["text"])):
                chunks.append({
                    "text": chunk_text,
                    "metadata": {
                        "source_url": page["url"],
                        "page_title": page["title"],
                        "chunk_index": i,
                        "ingested_at": datetime.now(timezone.utc).isoformat(),
                        "chunk_id": hashlib.md5(chunk_text.encode()).hexdigest(),
                    },
                })
        return chunks

    def _upsert(self, chunks: list[dict], refresh: bool = False) -> int:
        import shutil, os
        persist_path = os.path.abspath(settings.chroma_persist_dir)
        if refresh and os.path.exists(persist_path):
            shutil.rmtree(persist_path)
            logger.info("Dropped existing ChromaDB data for refresh.")
        os.makedirs(persist_path, exist_ok=True)
        client = chromadb.PersistentClient(path=persist_path)

        # Deduplicate by chunk_id before upserting — same content can be
        # reached via multiple URLs during the crawl, producing identical hashes.
        seen: set[str] = set()
        unique_chunks: list[dict] = []
        for c in chunks:
            cid = c["metadata"]["chunk_id"]
            if cid not in seen:
                seen.add(cid)
                unique_chunks.append(c)
        logger.info("Deduped %d → %d unique chunks", len(chunks), len(unique_chunks))

        # Use native chromadb client directly — bypasses langchain-chroma
        # metadata _type incompatibility with chromadb 0.6.x
        collection = client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )
        texts = [c["text"] for c in unique_chunks]
        embeddings_list = self._embeddings.embed_documents(texts)
        collection.add(
            ids=[c["metadata"]["chunk_id"] for c in unique_chunks],
            embeddings=embeddings_list,
            documents=texts,
            metadatas=[c["metadata"] for c in unique_chunks],
        )
        return len(unique_chunks)
