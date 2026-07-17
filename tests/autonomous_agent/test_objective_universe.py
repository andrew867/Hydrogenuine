"""Objective universe tests."""
from __future__ import annotations

import tempfile
from pathlib import Path

from hg_runtime.task_selection.objective_universe import ObjectiveUniverse, create_demo_universe


def test_universe_hash_deterministic():
    body = {
        "universe_id": "u1",
        "agent_id": "zero",
        "allowed_objective_scopes": ["internal:artifacts"],
        "blocked_objective_scopes": ["external:live_publish"],
        "allowed_task_types": ["review_local_artifacts"],
        "blocked_task_types": ["publish_live"],
        "external_action_policy_ref": "configs/agent_zero/external_write_authority_policy.json",
        "status": "active",
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    u = ObjectiveUniverse(**body, expires_at=None, hash=None).with_hash()
    u2 = ObjectiveUniverse(**body, expires_at=None, hash=None).with_hash()
    assert u.hash == u2.hash


def test_universe_blocks_forbidden_scope(tmp_path, monkeypatch):
    monkeypatch.setattr("hg_runtime.task_selection.objective_universe.UNIVERSE_DIR", tmp_path / "universes")
    u = create_demo_universe()
    assert u.scope_allowed("internal:artifacts") is True
    assert u.scope_allowed("external:live_publish") is False


def test_task_type_blocked():
    u = ObjectiveUniverse(
        universe_id="u",
        agent_id="zero",
        allowed_objective_scopes=("internal:a",),
        blocked_objective_scopes=(),
        allowed_task_types=("review_local_artifacts",),
        blocked_task_types=("publish_live",),
        external_action_policy_ref="ref",
        status="active",
        created_at="t",
    )
    assert u.task_type_allowed("publish_live") is False
