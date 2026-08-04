"""Unit: eval prefer_live context flag."""

from shorts_assistant.eval_flags import live_judge_mode, prefer_live_judge


def test_prefer_live_default_false():
    assert prefer_live_judge() is False


def test_live_judge_mode_context():
    assert prefer_live_judge() is False
    with live_judge_mode(True):
        assert prefer_live_judge() is True
    assert prefer_live_judge() is False
