"""Application configuration loaded from environment / ``.env``.

Purpose: one place for runtime knobs (API keys, model name, logging) so nodes
and CLI do not hard-code secrets or scatter ``os.environ`` reads.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root: src/shorts_assistant/config.py → parents[2]
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Purpose: typed runtime settings for the Shorts assistant process.

    Why it exists: Gemini credentials, model id, and later persistence/OTEL
    flags must be validated and documented in one schema (see ``.env.example``).

    Written by: environment variables / ``.env`` at process start.
    Read by: live LLM calls (when enabled), logging, future persistence/API.
    """

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    google_genai_use_vertexai: str = Field(
        default="FALSE", alias="GOOGLE_GENAI_USE_VERTEXAI"
    )

    model_name: str = Field(default="gemini-2.0-flash-001", alias="MODEL_NAME")
    app_name: str = Field(default="youtube_shorts_app", alias="APP_NAME")

    database_url: str = Field(
        default=f"sqlite+pysqlite:///{PROJECT_ROOT / 'data' / 'shorts.db'}",
        alias="DATABASE_URL",
    )
    session_db_url: str = Field(
        default="",
        alias="SESSION_DB_URL",
        description="Deprecated alias for DATABASE_URL (ADK-era name).",
    )
    checkpoint_backend: str = Field(default="memory", alias="CHECKPOINT_BACKEND")
    checkpoint_postgres_url: str = Field(
        default="", alias="CHECKPOINT_POSTGRES_URL"
    )
    max_input_length: int = Field(default=2000, alias="MAX_INPUT_LENGTH")
    enable_otel: bool = Field(default=False, alias="ENABLE_OTEL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    quality_threshold: float = Field(default=7.0, alias="QUALITY_THRESHOLD", ge=0, le=10)

    llm_timeout_seconds: float = Field(
        default=30.0, alias="LLM_TIMEOUT_SECONDS", gt=0
    )
    llm_max_attempts: int = Field(default=3, alias="LLM_MAX_ATTEMPTS", ge=1)
    llm_backoff_base_seconds: float = Field(
        default=0.5, alias="LLM_BACKOFF_BASE_SECONDS", ge=0
    )
    llm_backoff_max_seconds: float = Field(
        default=8.0, alias="LLM_BACKOFF_MAX_SECONDS", gt=0
    )
    live_judge_fallback: bool = Field(default=True, alias="LIVE_JUDGE_FALLBACK")

    log_payloads: bool = Field(default=False, alias="LOG_PAYLOADS")
    cost_per_1m_input_usd: float = Field(
        default=0.10, alias="COST_PER_1M_INPUT_USD", ge=0
    )
    cost_per_1m_output_usd: float = Field(
        default=0.40, alias="COST_PER_1M_OUTPUT_USD", ge=0
    )

    @field_validator("google_api_key")
    @classmethod
    def api_key_required_unless_vertex(cls, value: str) -> str:
        """Purpose: trim whitespace from the API key; empty is allowed until live run."""
        return value.strip() if value else ""

    def validate_for_runtime(self) -> None:
        """Purpose: fail fast before a live Gemini call if credentials are missing.

        Why it exists: demo/offline graph does not need a key; live judge/script
        paths should call this first so failures are clear.
        """
        use_vertex = self.google_genai_use_vertexai.upper() in {
            "TRUE",
            "1",
            "YES",
        }
        if not use_vertex and not self.google_api_key:
            raise ValueError(
                "GOOGLE_API_KEY is required when GOOGLE_GENAI_USE_VERTEXAI is not TRUE."
            )


@lru_cache
def get_settings() -> Settings:
    """Purpose: return one cached Settings instance for the process."""
    return Settings()


settings = get_settings()
