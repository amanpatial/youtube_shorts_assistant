"""Pydantic input validation for shorts_catalog MCP tools."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ListRecentShortsArgs(BaseModel):
    """Purpose: validate list_recent_shorts arguments."""

    limit: int = Field(default=5, ge=1, le=20)


class SearchShortsArgs(BaseModel):
    """Purpose: validate search_shorts arguments."""

    query: str = Field(min_length=1, max_length=200)
    limit: int = Field(default=5, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("query must be non-empty")
        return cleaned


class GetShortArgs(BaseModel):
    """Purpose: validate get_short arguments."""

    execution_id: UUID
