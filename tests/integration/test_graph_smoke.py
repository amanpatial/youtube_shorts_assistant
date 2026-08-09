"""Integration: compiled graph offline smoke (demo producers, no live LLM)."""

from shorts_assistant import __version__, get_compiled_graph
from shorts_assistant.graph import build_graph
from shorts_assistant.run import invoke_workflow
from shorts_assistant.state import WorkflowState, WorkflowStatus


def test_package_version():
    assert __version__ == "0.23.0"


def test_build_graph_compiles():
    compiled = build_graph().compile()
    assert compiled is not None


def test_pipeline_invoke_completed(tmp_path, monkeypatch):
    db = tmp_path / "smoke.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db}")
    monkeypatch.setenv("CHECKPOINT_BACKEND", "memory")
    from shorts_assistant.checkpointer import reset_checkpointer_for_tests
    from shorts_assistant.config import get_settings
    from shorts_assistant.persistence.session import reset_engine_cache

    get_settings.cache_clear()
    reset_engine_cache()
    reset_checkpointer_for_tests()
    import shorts_assistant.checkpointer as cp
    import shorts_assistant.config as cfg
    import shorts_assistant.persistence.session as sess

    monkeypatch.setattr(cfg, "settings", get_settings())
    monkeypatch.setattr(sess, "settings", get_settings())
    monkeypatch.setattr(cp, "settings", get_settings())

    final = invoke_workflow("LangGraph hygiene")
    assert final.status == WorkflowStatus.COMPLETED
    assert final.request == "LangGraph hygiene"
    assert final.generated_script is not None
    assert final.trace_id
    assert final.trace_id.startswith("wf_")
    assert final.execution_id
    assert final.error_class is None
    assert final.error_node is None


def test_workflow_state_keys_present():
    result = get_compiled_graph(with_checkpointer=False).invoke(
        WorkflowState.initial("x").to_dict()
    )
    assert "request" in result
    assert "generated_script" in result
    assert "evaluation" in result
    assert "visual_concepts" in result
    assert "final_short_concept" in result
