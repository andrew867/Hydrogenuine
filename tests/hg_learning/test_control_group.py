from __future__ import annotations

import os

from hg_realtime.swarm.nodes import CONTROL_GROUP_PERCENT, is_learning_control_group, swarm_spawn
from hg_realtime.swarm.contracts import SwarmPlan


def test_control_group_disabled_by_default(monkeypatch):
    monkeypatch.delenv("HG_LEARNING_CONTROL_GROUP_ENABLED", raising=False)
    monkeypatch.delenv("HG_LEARNING_LIVE_FEEDBACK_ENABLED", raising=False)
    assert is_learning_control_group("corr-123") is False


def test_control_group_enabled_with_l3_master(monkeypatch):
    monkeypatch.delenv("HG_LEARNING_CONTROL_GROUP_ENABLED", raising=False)
    monkeypatch.setenv("HG_LEARNING_LIVE_FEEDBACK_ENABLED", "1")
    in_group = sum(1 for i in range(500) if is_learning_control_group(f"corr-{i}"))
    assert 30 <= in_group <= 80


def test_control_group_assignment_when_enabled(monkeypatch):
    monkeypatch.setenv("HG_LEARNING_CONTROL_GROUP_ENABLED", "1")
    in_group = sum(1 for i in range(500) if is_learning_control_group(f"corr-{i}"))
    assert 30 <= in_group <= 80


def test_swarm_spawn_tags_control_group(monkeypatch):
    monkeypatch.setenv("HG_LEARNING_CONTROL_GROUP_ENABLED", "1")
    plan = SwarmPlan(summary="test", tasks=[{"workflow_id": "w1", "inputs": {}}], max_children=2)
    children = swarm_spawn(plan=plan, correlation_id="corr-test-42", learning_control_group=True)
    assert children[0]["learning_control_group"] is True
    assert children[0]["learning_priors_enabled"] is False


def test_control_group_percent_constant():
    assert CONTROL_GROUP_PERCENT == 10
