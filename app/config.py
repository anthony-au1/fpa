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
