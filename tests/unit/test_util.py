"""Tests for instruction loading helpers."""

from pathlib import Path

from shorts_assistant.util import load_instruction_from_file


def test_load_instruction_success(tmp_path):
    path = tmp_path / "sample_instruction.txt"
    path.write_text("Pro Short for raw_idea topics.", encoding="utf-8")
    text = load_instruction_from_file("sample_instruction.txt", base_dir=tmp_path)
    assert "Pro Short" in text
    assert "raw_idea" in text


def test_load_instruction_missing_file_uses_default():
    default = "fallback-instruction"
    text = load_instruction_from_file(
        "definitely_missing_instruction_file_xyz.txt",
        default_instruction=default,
    )
    assert text == default


def test_archived_prompt_files_exist():
    root = Path(__file__).resolve().parents[2] / "archive" / "adk_baseline"
    for name in (
        "scriptwriter_instruction.txt",
        "visualizer_instruction.txt",
        "formatter_instruction.txt",
        "critic_instruction.txt",
    ):
        assert (root / name).is_file(), f"missing archived prompt: {name}"
