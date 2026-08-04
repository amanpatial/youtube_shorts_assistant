"""Centralized application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """Runtime configuration for the YouTube Shorts Assistant."""

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

    session_db_url: str = Field(
        default=f"sqlite+aiosqlite:///{PROJECT_ROOT / 'data' / 'sessions.db'}",
        alias="SESSION_DB_URL",
    )
    max_input_length: int = Field(default=2000, alias="MAX_INPUT_LENGTH")
    enable_otel: bool = Field(default=False, alias="ENABLE_OTEL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @field_validator("google_api_key")
    @classmethod
    def api_key_required_unless_vertex(cls, value: str) -> str:
        # Vertex AI can use ADC instead of an API key; allow empty in that case.
        return value.strip() if value else ""

    def validate_for_runtime(self) -> None:
        """Fail fast when credentials needed for a normal API-key run are missing."""
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
    return Settings()


settings = get_settings()
