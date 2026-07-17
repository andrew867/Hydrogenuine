"""Broker integration for task selection."""
from __future__ import annotations

import pytest

from hg_runtime.capability_broker.action_registry import is_forbidden_action, is_known_action
from hg_runtime.task_selection.objective_universe import ObjectiveUniverse
from hg_runtime.task_selection.schema import AllowedTaskType
from hg_runtime.task_selection.task_candidate import TaskCandidate
from hg_runtime.task_selection.task_selector import TaskSelectionContext, select_next_task


@pytest.fixture
def store_dirs(tmp_path, monkeypatch):
    root = tmp_path / "task_selection"
    monkeypatch.setattr("hg_runtime.task_selection.schema.STORE_ROOT", root)
    monkeypatch.setattr("hg_runtime.task_selection.task_receipts.STORE_ROOT", root)
    monkeypatch.setattr("hg_runtime.task_selection.task_receipts.DECISION_DIR", root / "decisions")
    monkeypatch.setattr("hg_runtime.task_selection.task_receipts.RECEIPT_DIR", root / "receipts")
    return root


def test_broker_not_bypassed_forbidden():
    for action in ("publish", "send", "reply_live", "comment_live", "browser_submit", "hardware_actuate"):
        assert is_forbidden_action(action)


def test_prepare_uses_broker_action(store_dirs):
    universe = ObjectiveUniverse(
        universe_id="u",
        agent_id="zero",
        allowed_objective_scopes=("internal:external_write_candidate",),
        blocked_objective_scopes=(),
        allowed_task_types=(AllowedTaskType.PREPARE_EXTERNAL_ACTION_CANDIDATE.value,),
        blocked_task_types=(),
        external_action_policy_ref="ref",
        status="active",
        created_at="t",
    )
    cand = TaskCandidate(
        task_candidate_id="c1",
        objective_scope_ref="internal:external_write_candidate",
        task_type=AllowedTaskType.PREPARE_EXTERNAL_ACTION_CANDIDATE.value,
        title="prep",
        risk_class="low",
        requires_external_action=False,
        requires_operator_review=True,
        status="candidate",
        created_at="2026-01-01T00:00:00+00:00",
    ).with_hash()
    result = select_next_task(TaskSelectionContext(universe=universe, candidates=[cand], run_id="r"))
    assert result.decision.broker_decision_ref is not None
    assert is_known_action("create_external_action_candidate")


def test_provider_suggestion_cannot_grant_authority(store_dirs):
    from hg_runtime.task_selection.task_policy import evaluate_candidate_policy

    ok, reason = evaluate_candidate_policy(
        task_type="publish_live",
        objective_scope="internal:a",
        scope_allowed=True,
        requires_external_action=True,
        model_suggested=True,
    )
    assert ok is False
