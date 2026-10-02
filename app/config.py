from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite:///./data/app.db"
    corpus_path: Path = Path("finance_rag_corpus")
    index_path: Path = Path("data/index")
    rag_embedding_provider: str = "local_tfidf"
    rag_chunk_max_chars: int = Field(default=1800, ge=400, le=10000)
    rag_retrieval_timeout_seconds: float = Field(default=2, gt=0)
    rag_bm25_weight: float = Field(default=0.5, ge=0, le=1)
    rag_vector_weight: float = Field(default=0.35, ge=0, le=1)
    rag_metadata_weight: float = Field(default=0.15, ge=0, le=1)
    llm_provider: str = "disabled"
    llm_model: str = "luna"
    llm_complex_model: str = "terra"
    llm_timeout_seconds: float = Field(default=30, gt=0)
    llm_max_retries: int = Field(default=2, ge=0)
    agent_max_steps: int = Field(default=20, ge=1)
    agent_max_tool_calls: int = Field(default=12, ge=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
