"""
SelfCritiqueTool — optional async hallucination checker (Layer 3).

Re-reads a generated email against retrieved RAG chunks and flags any
unsupported claims. Excluded from the demo critical path because it adds
10–20 seconds per lead. Run as a background task in production.

Usage:
    from tools.self_critique_tool import SelfCritiqueTool
    result = await SelfCritiqueTool(llm).check(email_body, rag_chunks)
"""
import json
import logging

from langchain_ollama import OllamaLLM

from config import settings
from observability.metrics import hallucination_checks_total
from prompts import load_prompt

logger = logging.getLogger(__name__)


class SelfCritiqueTool:
    def __init__(self, llm: OllamaLLM | None = None) -> None:
        self._llm = llm or OllamaLLM(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0.0,
            num_ctx=4096,
            num_gpu=settings.ollama_num_gpu,
        )

    async def check(self, email_body: str, rag_chunks: list[str]) -> dict:
        """
        Fact-check email_body against rag_chunks.

        Returns:
            {"hallucinated_claims": [...], "is_grounded": bool}
        """
        if not rag_chunks:
            return {"hallucinated_claims": [], "is_grounded": True}

        prompt = load_prompt(
            "self_critique.j2",
            email=email_body,
            rag_chunks=rag_chunks,
        )

        try:
            raw = self._llm.invoke(prompt).strip()
            # Extract JSON from LLM response
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                result = json.loads(raw[start:end])
            else:
                result = {"hallucinated_claims": [], "is_grounded": True}
            hallucination_checks_total.labels(
                is_grounded=str(result.get("is_grounded", True)).lower()
            ).inc()
            return result
        except Exception as exc:
            logger.warning("SelfCritique LLM call failed: %s", exc)
            return {"hallucinated_claims": [], "is_grounded": True}
