"""Unit tests for Phase 18 AI quality gate (deterministic)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shorts_assistant.eval_gate.gate import (
    GateConfig,
    evaluate_gate,
    evaluate_gate_files,
    load_gate_config,
)


def _artifact(
    *,
    mode: str = "demo",
    pass_rate: float = 1.0,
    average_quality: float = 8.5,
    failure_rate: float = 0.0,
    run_id: str = "run-a",
) -> dict:
    return {
        "summary": {
            "mode": mode,
            "pass_rate": pass_rate,
            "average_quality": average_quality,
            "failure_rate": failure_rate,
            "average_iterations": 1.0,
            "approval_rate": 1.0,
            "run_id": run_id,
        }
    }


def test_load_gate_config(tmp_path: Path) -> None:
    p = tmp_path / "quality_gate.yaml"
    p.write_text(
        "min_pass_rate_delta: -0.05\n"
        "min_average_quality_delta: -0.3\n"
        "max_failure_rate: 0.15\n"
        "max_failure_rate_delta: 0.05\n",
        encoding="utf-8",
    )
    cfg = load_gate_config(p)
    assert cfg.min_pass_rate_delta == -0.05
    assert cfg.max_failure_rate == 0.15


def test_gate_passes_on_improvement() -> None:
    base = _artifact(pass_rate=0.8, average_quality=8.0, failure_rate=0.1)
    cand = _artifact(pass_rate=0.95, average_quality=8.8, failure_rate=0.05, run_id="run-b")
    result = evaluate_gate(base, cand, GateConfig())
    assert result.passed
    assert result.reasons == []


def test_gate_fails_on_pass_rate_regression() -> None:
    base = _artifact(pass_rate=1.0, average_quality=8.5)
    cand = _artifact(pass_rate=0.9, average_quality=8.5, run_id="run-b")  # −10pp
    result = evaluate_gate(base, cand, GateConfig())
    assert not result.passed
    assert any("pass_rate" in r for r in result.reasons)


def test_gate_fails_on_quality_regression() -> None:
    base = _artifact(average_quality=8.5)
    cand = _artifact(average_quality=8.0, run_id="run-b")  # −0.5
    result = evaluate_gate(base, cand, GateConfig())
    assert not result.passed
    assert any("average_quality" in r for r in result.reasons)


def test_gate_fails_on_absolute_failure_rate() -> None:
    base = _artifact(failure_rate=0.0)
    cand = _artifact(failure_rate=0.2, run_id="run-b")
    result = evaluate_gate(base, cand, GateConfig())
    assert not result.passed
    assert any("max_failure_rate" in r for r in result.reasons)


def test_gate_fails_on_failure_rate_delta() -> None:
    base = _artifact(failure_rate=0.0)
    cand = _artifact(failure_rate=0.1, run_id="run-b")  # +10pp > 5pp
    result = evaluate_gate(base, cand, GateConfig(max_failure_rate=0.5))
    assert not result.passed
    assert any("failure_rate delta" in r for r in result.reasons)


def test_gate_fails_closed_missing_baseline(tmp_path: Path) -> None:
    cand = tmp_path / "cand.json"
    cand.write_text(json.dumps(_artifact()), encoding="utf-8")
    cfg = tmp_path / "quality_gate.yaml"
    cfg.write_text("max_failure_rate: 0.15\n", encoding="utf-8")
    result = evaluate_gate_files(tmp_path / "missing.json", cand, cfg)
    assert not result.passed
    assert any("baseline missing" in r for r in result.reasons)


def test_gate_mode_mismatch_fails() -> None:
    base = _artifact(mode="demo")
    cand = _artifact(mode="live_judge", run_id="run-b")
    result = evaluate_gate(base, cand, GateConfig())
    assert not result.passed
    assert any("mode mismatch" in r for r in result.reasons)


def test_cli_exit_codes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from shorts_assistant.eval_gate.__main__ import main

    base_p = tmp_path / "base.json"
    cand_ok = tmp_path / "ok.json"
    cand_bad = tmp_path / "bad.json"
    cfg = tmp_path / "quality_gate.yaml"
    base_p.write_text(json.dumps(_artifact()), encoding="utf-8")
    cand_ok.write_text(json.dumps(_artifact(run_id="ok")), encoding="utf-8")
    cand_bad.write_text(json.dumps(_artifact(pass_rate=0.5, run_id="bad")), encoding="utf-8")
    cfg.write_text(
        "min_pass_rate_delta: -0.05\n"
        "min_average_quality_delta: -0.3\n"
        "max_failure_rate: 0.15\n"
        "max_failure_rate_delta: 0.05\n",
        encoding="utf-8",
    )
    assert (
        main(
            [
                "--baseline",
                str(base_p),
                "--candidate",
                str(cand_ok),
                "--config",
                str(cfg),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "--baseline",
                str(base_p),
                "--candidate",
                str(cand_bad),
                "--config",
                str(cfg),
            ]
        )
        == 1
    )
