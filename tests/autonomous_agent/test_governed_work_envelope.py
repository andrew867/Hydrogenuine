"""Governed work envelope tests."""
from __future__ import annotations

from hg_runtime.governed_work_loop.work_envelope import ExternalActionEnvelope, GovernedWorkEnvelope, create_demo_envelope


def test_envelope_hash_deterministic():
    body = {
        "envelope_id": "e1",
        "agent_id": "zero",
        "objective_universe_ref": "u1",
        "allowed_work_scopes": ("internal:a",),
        "blocked_work_scopes": ("external:live_unscoped",),
        "allowed_internal_actions": ("review_local_artifacts",),
        "allowed_external_candidate_types": ("publish_post",),
        "allowed_live_external_actions": (),
        "external_action_quota_ref": "q",
        "external_write_policy_ref": "w",
        "status": "active",
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    e1 = GovernedWorkEnvelope(**body, expires_at=None, hash=None).with_hash()
    e2 = GovernedWorkEnvelope(**body, expires_at=None, hash=None).with_hash()
    assert e1.hash == e2.hash


def test_envelope_blocks_forbidden_scope():
    e = GovernedWorkEnvelope(
        envelope_id="e",
        agent_id="zero",
        objective_universe_ref="u",
        allowed_work_scopes=("internal:a",),
        blocked_work_scopes=("external:live_unscoped",),
        allowed_internal_actions=(),
        allowed_external_candidate_types=(),
        allowed_live_external_actions=(),
        external_action_quota_ref="q",
        external_write_policy_ref="w",
        status="active",
        created_at="t",
    )
    assert e.scope_allowed("external:live_unscoped") is False


def test_external_envelope_max_live_default_zero(tmp_path, monkeypatch):
    monkeypatch.setattr("hg_runtime.governed_work_loop.work_envelope.STORE_ROOT", tmp_path)
    _, ext = create_demo_envelope()
    assert ext.max_live_dispatches == 0
    assert ext.live_dispatch_allowed is False
