"""Contract: agent/node invariants (no live LLM)."""

from tests.helpers import load_script_fixture

from shorts_assistant.nodes import evaluator_node
from shorts_assistant.schemas import ScriptEvaluation
from shorts_assistant.state import WorkflowState, WorkflowStatus


def test_evaluator_never_writes_generated_script():
    script = load_script_fixture("high_quality.json")
    state = WorkflowState.initial("typed state").apply_update(
        generated_script=script,
        status=WorkflowStatus.SCRIPTING,
    )
    update = evaluator_node(state)
    assert "generated_script" not in update
    assert update["status"] == WorkflowStatus.EVALUATING
    assert isinstance(update["evaluation"], ScriptEvaluation)
    assert state.generated_script == script
