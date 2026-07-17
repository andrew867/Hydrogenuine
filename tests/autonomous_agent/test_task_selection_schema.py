"""Task selection schema tests."""
from __future__ import annotations

from hg_runtime.task_selection.schema import (
    AllowedTaskType,
    BLOCKED_TASK_TYPES,
    TaskSelectionVerdict,
    load_task_selection_policy,
)


def test_allowed_task_types():
    assert AllowedTaskType.REVIEW_LOCAL_ARTIFACTS.value == "review_local_artifacts"
    assert "publish_live" in BLOCKED_TASK_TYPES


def test_policy_loads():
    policy = load_task_selection_policy()
    assert policy["phase"] == 21
    assert policy["zero_may_choose_tasks"] is True
    assert policy["zero_may_expand_objective_universe"] is False


def test_verdict_enums():
    assert TaskSelectionVerdict.GREEN_TASK_SELECTED.value.startswith("GREEN_")
