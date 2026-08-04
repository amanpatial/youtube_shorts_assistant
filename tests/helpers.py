"""Shared test helpers (importable without depending on pytest conftest)."""

from __future__ import annotations

import json
from pathlib import Path

from shorts_assistant.schemas import ShortScript

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
SCRIPTS_DIR = FIXTURES_DIR / "scripts"


def load_script_fixture(name: str) -> ShortScript:
    """Purpose: load a validated ShortScript from ``tests/fixtures/scripts``."""
    data = json.loads((SCRIPTS_DIR / name).read_text(encoding="utf-8"))
    return ShortScript.model_validate(data)
