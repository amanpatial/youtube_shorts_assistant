"""Small file helpers used by the package.

Purpose: load prompt/instruction text from disk without crashing if a file is missing.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def load_instruction_from_file(
    filename: str,
    default_instruction: str = "Default instruction.",
    *,
    base_dir: Path | None = None,
) -> str:
    """Purpose: read a prompt/instruction ``.txt`` file into a string.

    Why it exists: node prompts live as files under ``prompts/`` (or archive);
    code should load them in one place instead of embedding long strings.

    Returns: file contents, or ``default_instruction`` if missing/unreadable.
    Prefer: ``base_dir=Path(__file__).parent / "prompts"`` at call sites.
    """
    root = base_dir if base_dir is not None else Path(__file__).resolve().parent
    filepath = root / filename
    try:
        instruction = filepath.read_text(encoding="utf-8")
        logger.info("Loaded instruction from %s", filepath)
        return instruction
    except FileNotFoundError:
        logger.warning("Instruction file not found: %s. Using default.", filepath)
    except OSError as exc:
        logger.error(
            "Error loading instruction file %s: %s. Using default.",
            filepath,
            exc,
        )
    return default_instruction
