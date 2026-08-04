"""Shared helpers for loading agent instruction files."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def load_instruction_from_file(
    filename: str, default_instruction: str = "Default instruction."
) -> str:
    """Reads instruction text from a file relative to this module."""
    filepath = os.path.join(os.path.dirname(__file__), filename)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            instruction = f.read()
        logger.info("Loaded instruction from %s", filename)
        return instruction
    except FileNotFoundError:
        logger.warning(
            "Instruction file not found: %s. Using default.", filepath
        )
    except OSError as exc:
        logger.error(
            "Error loading instruction file %s: %s. Using default.",
            filepath,
            exc,
        )
    return default_instruction
