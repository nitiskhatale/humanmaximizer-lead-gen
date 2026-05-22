"""
LangSmith tracing setup.

Calling configure_tracing() at app startup enables LangSmith tracing for
every LangChain and LangGraph call when LANGCHAIN_API_KEY is set.
No-op when the key is absent so the app runs without any observability config.
"""
import logging
import os

from config import settings

logger = logging.getLogger(__name__)


def configure_tracing() -> None:
    """Set LangSmith environment variables from Pydantic settings."""
    if not settings.langchain_api_key:
        logger.info("LANGCHAIN_API_KEY not set — LangSmith tracing disabled")
        return

    os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    logger.info(
        "LangSmith tracing enabled (project='%s')", settings.langchain_project
    )
