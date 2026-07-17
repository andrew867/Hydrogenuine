"""Governed work loop schema tests."""
from __future__ import annotations

from hg_runtime.governed_work_loop.schema import ALLOWED_WORK_TYPES, BLOCKED_WORK_TYPES, load_governed_work_policy


def test_policy_phase_23():
    p = load_governed_work_policy()
    assert p["phase"] == 23
    assert p["zero_may_live_dispatch_by_default"] is False


def test_blocked_types():
    assert "publish_live_unscoped" in BLOCKED_WORK_TYPES
    assert "prepare_external_action_candidate" not in BLOCKED_WORK_TYPES
