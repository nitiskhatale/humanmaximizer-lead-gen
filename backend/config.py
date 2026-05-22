from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # LLM
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral:7b-instruct-v0.3-q4_K_M"
    ollama_num_gpu: int = 1

    # Vector DB
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_collection: str = "humanmaximizer_knowledge"
    chroma_persist_dir: str = "./chroma_db"

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/leads.db"

    # Search
    serpapi_key: Optional[str] = None

    # Observability
    langchain_api_key: Optional[str] = None
    langchain_project: str = "humanmaximizer-lead-gen"
    langchain_tracing_v2: bool = False
    slack_webhook_url: Optional[str] = None

    # App
    app_env: str = "development"
    log_level: str = "INFO"



settings = Settings()
