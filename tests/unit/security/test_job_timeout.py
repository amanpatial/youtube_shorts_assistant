"""Worker wall-clock timeout (Phase 17)."""

from __future__ import annotations

import pytest

from shorts_assistant.config import Settings
from shorts_assistant.worker.bridge import _run_with_timeout


def test_job_timeout_raises(monkeypatch):
    import shorts_assistant.worker.bridge as bridge

    monkeypatch.setattr(bridge, "settings", Settings(_env_file=None, job_timeout_sec=0.05))

    def slow() -> str:
        import time

        time.sleep(1.0)
        return "done"

    with pytest.raises(TimeoutError, match="JOB_TIMEOUT_SEC"):
        _run_with_timeout(slow)
