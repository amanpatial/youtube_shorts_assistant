"""Deterministic tests for eval dataset loading."""

import pytest
from pydantic import ValidationError

from shorts_assistant.config import PROJECT_ROOT
from shorts_assistant.eval.dataset import EvalDataset, load_dataset

DATASET = PROJECT_ROOT / "evals" / "shorts_v1_dataset.json"


def test_dataset_loads_20_unique_cases():
    ds = load_dataset(DATASET)
    assert ds.dataset_id == "shorts_v1"
    assert len(ds.cases) == 20
    ids = [c.case_id for c in ds.cases]
    assert len(ids) == len(set(ids))
    for case in ds.cases:
        assert case.input.topic.strip()
        assert case.quality_criteria.min_overall_score >= 0
        assert case.quality_criteria.must_include_sections


def test_duplicate_case_id_rejected():
    with pytest.raises(ValidationError):
        EvalDataset.model_validate(
            {
                "dataset_id": "x",
                "version": "1",
                "cases": [
                    {
                        "case_id": "a",
                        "input": {"topic": "t1"},
                        "quality_criteria": {"min_overall_score": 7},
                    },
                    {
                        "case_id": "a",
                        "input": {"topic": "t2"},
                        "quality_criteria": {"min_overall_score": 7},
                    },
                ],
            }
        )


def test_dataset_file_exists():
    assert DATASET.is_file()
