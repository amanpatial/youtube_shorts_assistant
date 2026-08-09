"""Load and validate the offline Shorts evaluation dataset."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


class CaseInput(BaseModel):
    """Purpose: topic seed for one eval case."""

    topic: str = Field(min_length=1)
    audience: str | None = None
    constraints: list[str] = Field(default_factory=list)


class QualityCriteria(BaseModel):
    """Purpose: deterministic pass thresholds for a case (not LLM prose)."""

    min_overall_score: float = Field(ge=0, le=10)
    require_approved: bool = False
    max_duration_seconds: float = Field(default=60, gt=0)
    must_include_sections: list[str] = Field(default_factory=lambda: ["hook", "body", "cta"])


class EvalCase(BaseModel):
    """Purpose: one fixed dataset row for baseline/compare."""

    case_id: str = Field(min_length=1)
    input: CaseInput
    expected_characteristics: list[str] = Field(default_factory=list)
    quality_criteria: QualityCriteria
    known_failure_patterns: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class EvalDataset(BaseModel):
    """Purpose: versioned collection of eval cases."""

    dataset_id: str
    version: str
    description: str = ""
    cases: list[EvalCase]

    @field_validator("cases")
    @classmethod
    def unique_case_ids(cls, cases: list[EvalCase]) -> list[EvalCase]:
        ids = [c.case_id for c in cases]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate case_id in dataset")
        return cases


def load_dataset(path: str | Path) -> EvalDataset:
    """Purpose: read JSON dataset and validate schema."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return EvalDataset.model_validate(data)


def dataset_to_dict(dataset: EvalDataset) -> dict[str, Any]:
    """Purpose: JSON-friendly dump for embedding in run artifacts."""
    return dataset.model_dump(mode="json")
