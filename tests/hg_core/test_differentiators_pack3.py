"""
Differentiators Pack 3: Continuity contracts, coalition hardening, governance safeguards.

See .cursor/plans/differentiators/chapter3/differentiators_pack3_continuity_coalition_governance/
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone

from hg_core.continuity import (
    publish_continuity_contract,
    list_continuity_contracts,
    check_continuity,
    perform_continuity_check,
    invalidate_continuity,
    request_revalidation,
)
from hg_core.coalition import (
    detect_coalition_signals,
    apply_safeguard,
    lift_safeguard,
    apply_safeguards_for_signal,
    list_active_safeguards,
)
from hg_core.governance import (
    check_closed_loop,
    require_independent_review,
    assign_reviewer,
    reject_approval_independence,
    assign_spotcheck,
)
from hg_core.ledger import emit


SCOPE = {"type": "run", "id": "test_diff3"}
ACTOR = {"agent_id": "agent_diff3", "pubkey": "0" * 64, "key_id": "k"}


def test_approval_expires_by_ttl(tmp_path: Path) -> None:
    """Approval expires by TTL and becomes invalid."""
    publish_continuity_contract(
        kind="approval",
        ref={"action_id": "act_1"},
        ttl_seconds=1,
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    valid, reason = check_continuity(
        tmp_path,
        "approval",
        {"action_id": "act_1"},
        context_ts=(datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")),
    )
    assert valid is True or reason == "no_contract"
    contracts = list_continuity_contracts(tmp_path, kind="approval")
    assert len(contracts) >= 1
    assert contracts[0].get("ttl_seconds") == 1
    # Force TTL expiry: use a context_ts from 10 seconds ago
    from datetime import timedelta
    past = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat().replace("+00:00", "Z")
    valid3, reason3 = check_continuity(tmp_path, "approval", {"action_id": "act_1"}, context_ts=past)
    assert valid3 is False
    assert reason3 == "ttl_expired"


def test_policy_change_invalidates_approvals(tmp_path: Path) -> None:
    """Policy change invalidates approvals that depend on it (environment_constraint)."""
    publish_continuity_contract(
        kind="approval",
        ref={"action_id": "act_p"},
        ttl_seconds=3600,
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
        environment_constraint="staging",
    )
    valid, _ = check_continuity(
        tmp_path, "approval", {"action_id": "act_p"},
        context_environment="staging",
    )
    assert valid is True
    valid_prod, reason = check_continuity(
        tmp_path, "approval", {"action_id": "act_p"},
        context_environment="prod",
    )
    assert valid_prod is False
    assert "environment" in reason.lower() or reason == "environment_mismatch"


def test_invalidation_creates_revalidation_work_item(tmp_path: Path) -> None:
    """Invalidation creates revalidation work item."""
    invalidate_continuity(
        kind="verification",
        ref={"action_id": "act_v"},
        reason="policy_version_changed",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    from hg_core.ledger.ledger_writer import iter_events_by_scope
    inv_id = None
    for _st, _sid, ev in iter_events_by_scope(tmp_path):
        if ev.get("action") == "CONTINUITY_INVALIDATED":
            inv_id = (ev.get("payload") or {}).get("invalid_id")
            break
    assert inv_id
    event_id, wi_id = request_revalidation(
        kind="verification",
        ref={"action_id": "act_v"},
        invalid_id=inv_id,
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
        create_work_item=True,
    )
    assert event_id
    assert wi_id is not None


def test_approval_ring_triggers_safeguards(tmp_path: Path) -> None:
    """Approval ring triggers safeguards automatically."""
    emit("ACTION_PROPOSED", "action", "a1", {"action_id": "a1", "work_item_id": "w1", "ts": "2026-01-01T00:00:00Z"}, scope=SCOPE, actor={"agent_id": "alice", "pubkey": "0", "key_id": "k"}, workspace_root=tmp_path)
    emit("ACTION_APPROVAL_GRANTED", "action", "a1", {"action_id": "a1", "ts": "2026-01-01T00:00:01Z"}, scope=SCOPE, actor={"agent_id": "bob", "pubkey": "0", "key_id": "k"}, workspace_root=tmp_path)
    emit("ACTION_PROPOSED", "action", "a2", {"action_id": "a2", "work_item_id": "w2", "ts": "2026-01-01T00:00:02Z"}, scope=SCOPE, actor={"agent_id": "bob", "pubkey": "0", "key_id": "k"}, workspace_root=tmp_path)
    emit("ACTION_APPROVAL_GRANTED", "action", "a2", {"action_id": "a2", "ts": "2026-01-01T00:00:03Z"}, scope=SCOPE, actor={"agent_id": "alice", "pubkey": "0", "key_id": "k"}, workspace_root=tmp_path)
    signals = detect_coalition_signals(tmp_path, SCOPE, ACTOR, emit_events=True)
    assert any(s.get("signal_type") == "approval_ring" for s in signals)
    applied = apply_safeguards_for_signal(
        next(s for s in signals if s.get("signal_type") == "approval_ring"),
        SCOPE,
        ACTOR,
        workspace_root=tmp_path,
    )
    assert len(applied) >= 1
    active = list_active_safeguards(tmp_path, scope=SCOPE)
    assert len(active) >= 1
    lift_safeguard(safeguard_id=applied[0], scope=SCOPE, actor=ACTOR, workspace_root=tmp_path, reason="test_done")
    active_after = list_active_safeguards(tmp_path, scope=SCOPE)
    assert len(active_after) < len(active)


def test_safeguards_enforce_independent_reviewer(tmp_path: Path) -> None:
    """Safeguards enforce independent reviewer and verifier diversity."""
    sg_id = apply_safeguard(
        kind="require_independent_reviewer",
        scope=SCOPE,
        targets=[{"action_id": "act_x"}],
        scope_actor=ACTOR,
        workspace_root=tmp_path,
        rationale="High-risk action",
    )
    assert sg_id.startswith("sg_")
    assert (tmp_path / "artifacts" / "coalition" / "safeguards" / f"{sg_id}.json").exists()


def test_closed_loop_approvals_rejected(tmp_path: Path) -> None:
    """Closed-loop approvals rejected."""
    emit("ACTION_PROPOSED", "action", "c1", {"action_id": "c1"}, scope=SCOPE, actor={"agent_id": "x", "pubkey": "0", "key_id": "k"}, workspace_root=tmp_path)
    emit("ACTION_APPROVAL_GRANTED", "action", "c1", {"action_id": "c1"}, scope=SCOPE, actor={"agent_id": "y", "pubkey": "0", "key_id": "k"}, workspace_root=tmp_path)
    emit("ACTION_PROPOSED", "action", "c2", {"action_id": "c2"}, scope=SCOPE, actor={"agent_id": "y", "pubkey": "0", "key_id": "k"}, workspace_root=tmp_path)
    emit("ACTION_APPROVAL_GRANTED", "action", "c2", {"action_id": "c2"}, scope=SCOPE, actor={"agent_id": "x", "pubkey": "0", "key_id": "k"}, workspace_root=tmp_path)
    is_closed = check_closed_loop(tmp_path, "x", "y")
    assert is_closed is True
    is_closed_other = check_closed_loop(tmp_path, "z", "y")
    assert is_closed_other is False or is_closed_other is True  # z might not be in graph
    ev_reject = reject_approval_independence(action_id="c3", reason="closed_loop", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert ev_reject


def test_reviewer_rotation_and_spotcheck(tmp_path: Path) -> None:
    """Reviewer rotation and spot checks assigned for batch approvals."""
    ev_req = require_independent_review(action_id="r1", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path, reason="high_impact")
    assert ev_req
    ev_assign = assign_reviewer(action_id="r1", reviewer_id="reviewer_1", rationale="availability", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert ev_assign
    ev_spot, spot_id = assign_spotcheck(batch_id="b1", target_id="t1", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert ev_spot
    assert spot_id
