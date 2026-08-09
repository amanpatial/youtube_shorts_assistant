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
        populate_by_name=True,
    )

    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    google_genai_use_vertexai: str = Field(default="FALSE", alias="GOOGLE_GENAI_USE_VERTEXAI")

    # Phase 19: local | staging | production (prod/staging fail-fast on boot)
    app_env: str = Field(default="local", alias="APP_ENV")

    model_name: str = Field(default="gemini-2.0-flash-001", alias="MODEL_NAME")
    # Phase 14: per-task overrides (empty → MODEL_NAME for parity)
    model_research: str = Field(default="", alias="MODEL_RESEARCH")
    model_write: str = Field(default="", alias="MODEL_WRITE")
    model_evaluate: str = Field(default="", alias="MODEL_EVALUATE")
    model_visualize: str = Field(default="", alias="MODEL_VISUALIZE")
    model_format: str = Field(default="", alias="MODEL_FORMAT")
    model_fallback: str = Field(default="", alias="MODEL_FALLBACK")
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
    checkpoint_postgres_url: str = Field(default="", alias="CHECKPOINT_POSTGRES_URL")
    max_input_length: int = Field(default=2000, alias="MAX_INPUT_LENGTH")
    enable_otel: bool = Field(default=False, alias="ENABLE_OTEL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    quality_threshold: float = Field(default=7.0, alias="QUALITY_THRESHOLD", ge=0, le=10)

    llm_timeout_seconds: float = Field(default=30.0, alias="LLM_TIMEOUT_SECONDS", gt=0)
    llm_max_attempts: int = Field(default=3, alias="LLM_MAX_ATTEMPTS", ge=1)
    llm_backoff_base_seconds: float = Field(default=0.5, alias="LLM_BACKOFF_BASE_SECONDS", ge=0)
    llm_backoff_max_seconds: float = Field(default=8.0, alias="LLM_BACKOFF_MAX_SECONDS", gt=0)
    live_judge_fallback: bool = Field(default=True, alias="LIVE_JUDGE_FALLBACK")

    log_payloads: bool = Field(default=False, alias="LOG_PAYLOADS")
    cost_per_1m_input_usd: float = Field(default=0.10, alias="COST_PER_1M_INPUT_USD", ge=0)
    cost_per_1m_output_usd: float = Field(default=0.40, alias="COST_PER_1M_OUTPUT_USD", ge=0)

    # Phase 11: long-term memory / RAG (not CHECKPOINT_BACKEND=memory)
    memory_retrieval: bool = Field(default=True, alias="MEMORY_RETRIEVAL")
    memory_top_k: int = Field(default=3, alias="MEMORY_TOP_K", ge=0, le=20)
    memory_max_context_chars: int = Field(default=1500, alias="MEMORY_MAX_CONTEXT_CHARS", ge=100)
    memory_write_min_score: float = Field(default=7.0, alias="MEMORY_WRITE_MIN_SCORE", ge=0, le=10)
    memory_retention_days: int = Field(default=180, alias="MEMORY_RETENTION_DAYS", ge=1)

    # Phase 12: MCP shorts_catalog (tools — not A2A)
    mcp_shorts_catalog_enabled: bool = Field(default=True, alias="MCP_SHORTS_CATALOG_ENABLED")
    mcp_tool_timeout_sec: float = Field(default=5.0, alias="MCP_TOOL_TIMEOUT_SEC", gt=0)
    mcp_allowed_tools: str = Field(
        default="list_recent_shorts,search_shorts,get_short",
        alias="MCP_ALLOWED_TOOLS",
    )

    # Phase 13: human-in-the-loop (default off so CI/eval never hang)
    hitl_required: bool = Field(default=False, alias="HITL_REQUIRED")
    max_human_rounds: int = Field(default=2, alias="MAX_HUMAN_ROUNDS", ge=0, le=10)

    # Phase 15: A2A Research Agent (default off — CI stays single-process)
    a2a_research_enabled: bool = Field(default=False, alias="A2A_RESEARCH_ENABLED")
    a2a_research_url: str = Field(default="http://127.0.0.1:9101", alias="A2A_RESEARCH_URL")
    a2a_timeout_sec: float = Field(default=30.0, alias="A2A_TIMEOUT_SEC", gt=0)
    a2a_research_required: bool = Field(default=False, alias="A2A_RESEARCH_REQUIRED")

    # Phase 16: async API + worker
    api_key: str = Field(default="", alias="API_KEY")
    api_keys: str = Field(
        default="",
        alias="API_KEYS",
        description="Optional comma-separated extra API keys",
    )
    worker_poll_sec: float = Field(default=1.0, alias="WORKER_POLL_SEC", gt=0)
    job_max_attempts: int = Field(default=3, alias="JOB_MAX_ATTEMPTS", ge=1, le=20)

    # Phase 17: security / guardrails
    api_rate_limit_per_min: int = Field(default=30, alias="API_RATE_LIMIT_PER_MIN", ge=1, le=10_000)
    job_timeout_sec: float = Field(default=300.0, alias="JOB_TIMEOUT_SEC", gt=0)
    force_hitl_on_injection: bool = Field(default=True, alias="FORCE_HITL_ON_INJECTION")
    output_policy_enabled: bool = Field(default=True, alias="OUTPUT_POLICY_ENABLED")

    @field_validator("google_api_key")
    @classmethod
    def api_key_required_unless_vertex(cls, value: str) -> str:
        """Purpose: trim whitespace from the API key; empty is allowed until live run."""
        return value.strip() if value else ""

    def _uses_vertex(self) -> bool:
        return self.google_genai_use_vertexai.upper() in {"TRUE", "1", "YES"}

    def validate_for_runtime(self) -> None:
        """Purpose: fail fast before a live Gemini call if credentials are missing.

        Why it exists: demo/offline graph does not need a key; live judge/script
        paths should call this first so failures are clear.
        """
        if not self._uses_vertex() and not self.google_api_key:
            raise ValueError(
                "GOOGLE_API_KEY is required when GOOGLE_GENAI_USE_VERTEXAI is not TRUE."
            )

    def validate_for_production(self) -> None:
        """Purpose: fail fast at API/worker boot when APP_ENV is staging/production.

        Why it exists: refuse SQLite, missing API keys, or missing Gemini creds
        before accepting traffic in a real deploy.
        """
        env = (self.app_env or "local").strip().lower()
        if env not in {"production", "prod", "staging"}:
            return

        url = (self.database_url or "").lower()
        if not url or "sqlite" in url:
            raise ValueError(
                "DATABASE_URL must be PostgreSQL when APP_ENV is staging/production "
                f"(got {self.database_url!r})."
            )
        if "postgres" not in url:
            raise ValueError(
                "DATABASE_URL must point at PostgreSQL when APP_ENV is staging/production."
            )

        primary = (self.api_key or "").strip()
        extras = (self.api_keys or "").strip()
        if not primary and not extras:
            raise ValueError("API_KEY or API_KEYS is required when APP_ENV is staging/production.")

        self.validate_for_runtime()


@lru_cache
def get_settings() -> Settings:
    """Purpose: return one cached Settings instance for the process."""
    return Settings()


settings = get_settings()
