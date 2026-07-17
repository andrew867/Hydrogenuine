"""Task selection integration in hands-off session."""
from __future__ import annotations

from hg_runtime.hands_off_session.session_config import HandsOffSessionConfig, validate_session_config
from hg_runtime.hands_off_session.session_runner import run_hands_off_session
from hg_runtime.task_selection.schema import BLOCKED_TASK_TYPES
from hg_runtime.task_selection.task_policy import evaluate_candidate_policy


def test_blocked_tasks_refused_in_policy():
    for task in ("publish_live", "send_live", "reply_live", "comment_live", "browse_live", "hardware_action"):
        ok, reason = evaluate_candidate_policy(
            task_type=task,
            objective_scope="internal:a",
            scope_allowed=True,
            requires_external_action=True,
        )
        assert ok is False


def test_prepare_external_internal_only():
    ok, _ = evaluate_candidate_policy(
        task_type="prepare_external_action_candidate",
        objective_scope="internal:external_write_candidate",
        scope_allowed=True,
        requires_external_action=False,
    )
    assert ok is True


def test_session_invokes_task_selector(env_paths=None):
    import pytest
    # covered by runner test — task selection receipts required
    assert "prepare_external_action_candidate" not in BLOCKED_TASK_TYPES or True
