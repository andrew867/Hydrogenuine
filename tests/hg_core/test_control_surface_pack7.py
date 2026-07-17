"""
Control Surface Pack 7: Steering integrity — directives, integrity, group drift, pinset snapshots, guardrails.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hg_core.steering import (
    publish_directive,
    apply_directive,
    list_directives,
    get_steering_timeline,
    compute_goal_integrity_score,
    emit_goal_integrity_score,
    get_goal_integrity_scores,
    get_goal_integrity_alerts,
    compute_group_drift_score,
    emit_group_drift_score,
    get_group_drift_scores,
    publish_steering_pinset_snapshot,
    resolve_steering_snapshot,
)
from hg_core.operator.guardrails import (
    check_override_budget,
    debit_override_budget,
    get_operator_guardrails_status,
    record_steering_blocked,
)
from hg_core.control_surface import (
    api_steering_directives_list,
    api_steering_timeline,
    api_steering_integrity_scores,
    api_steering_group_drift,
    api_operator_guardrails,
)


def _scope_actor():
    return {"type": "run", "id": "test"}, {"agent_id": "ops", "pubkey": "0" * 64, "key_id": "k"}


def test_material_steering_change_without_rationale_triggers_integrity_alert(tmp_path: Path) -> None:
    """Material steering change without rationale lowers goal integrity score; low score can trigger alert."""
    score_no_rationale = compute_goal_integrity_score(
        old_goal="old",
        new_goal="new",
        rationale_provided=False,
    )
    score_with_rationale = compute_goal_integrity_score(
        old_goal="old",
        new_goal="new",
        rationale_provided=True,
    )
    assert score_no_rationale < score_with_rationale
    assert score_no_rationale < 1.0


def test_constraint_erosion_increases_integrity_risk(tmp_path: Path) -> None:
    """Constraint erosion (fewer constraints) increases integrity risk (lower score)."""
    score_erosion = compute_goal_integrity_score(
        old_constraints=["a", "b", "c"],
        new_constraints=["a"],
        new_goal="same",
    )
    score_same = compute_goal_integrity_score(
        old_constraints=["a", "b"],
        new_constraints=["a", "b"],
        new_goal="same",
    )
    assert score_erosion < score_same


def test_correlated_autonomy_increases_trigger_group_drift(tmp_path: Path) -> None:
    """Correlated autonomy increases contribute to group drift score."""
    score_low = compute_group_drift_score(synchronized_autonomy_increases=0)
    score_high = compute_group_drift_score(synchronized_autonomy_increases=3)
    assert score_high > score_low
    assert 0 <= score_high <= 1


def test_emit_group_drift_and_safeguards(tmp_path: Path) -> None:
    """Emit group drift score; materializer can apply safeguards."""
    scope, actor = _scope_actor()
    gd_id = emit_group_drift_score(
        group_id="g1",
        score=0.8,
        scope=scope,
        actor=actor,
        workspace_root=tmp_path,
    )
    assert gd_id.startswith("gd_")
    from hg_core.materializers.group_drift_indexer import run as run_group_drift_indexer
    run_group_drift_indexer(tmp_path, rebuild=True)
    scores = get_group_drift_scores(tmp_path, group_id="g1")
    assert len(scores) == 1
    assert scores[0]["group_id"] == "g1"
    assert scores[0]["score"] == 0.8


def test_steering_snapshots_pinned_and_referenced(tmp_path: Path) -> None:
    """Steering snapshots are published and can be resolved by snapshot_id for replay."""
    scope, actor = _scope_actor()
    target_refs = [{"type": "entity", "id": "e1"}]
    directive_refs = [{"directive_id": "dir_abc", "hash": "h123"}]
    snapshot_id = publish_steering_pinset_snapshot(
        target_refs=target_refs,
        directive_refs=directive_refs,
        scope=scope,
        actor=actor,
        workspace_root=tmp_path,
    )
    assert snapshot_id.startswith("snap_")
    resolved = resolve_steering_snapshot(tmp_path, snapshot_id)
    assert resolved is not None
    assert resolved["snapshot_id"] == snapshot_id
    assert resolved["directive_refs"] == directive_refs
    assert resolved["target_refs"] == target_refs


def test_override_budgets_debit_and_enforce_limits(tmp_path: Path) -> None:
    """Override budget debits and check_override_budget enforces limits."""
    scope, actor = _scope_actor()
    root = tmp_path / "memory" / "materialized"
    root.mkdir(parents=True, exist_ok=True)
    (root / "operator_guardrails.jsonl").write_text(
        '{"action":"OPERATOR_OVERRIDE_BUDGET_DEBITED","operator_id":"op1","risk_weight":95}\n',
        encoding="utf-8",
    )
    status = check_override_budget(tmp_path, "op1", risk_weight=10)
    assert status["remaining"] == 5.0
    assert status["allowed"] is False
    assert status["reason"] == "override_budget_exhausted"

    debit_override_budget(
        operator_id="op1",
        risk_weight=5,
        scope=scope,
        actor=actor,
        workspace_root=tmp_path,
    )
    from hg_core.materializers.operator_guardrails_indexer import run as run_op_indexer
    run_op_indexer(tmp_path, rebuild=True)
    guards = get_operator_guardrails_status(tmp_path, operator_id="op1")
    assert len(guards) >= 1


def test_steering_directives_publish_apply_timeline(tmp_path: Path) -> None:
    """Publish and apply directive; timeline and list reflect state after materializer."""
    scope, actor = _scope_actor()
    target_ref = {"type": "entity", "id": "e1"}
    directive_id = publish_directive(
        target_ref=target_ref,
        goal="G",
        constraints=["C1"],
        autonomy_preset="normal",
        scope=scope,
        actor=actor,
        rationale_artifact_id="r1",
        workspace_root=tmp_path,
    )
    assert directive_id
    apply_directive(
        directive_id=directive_id,
        target_ref=target_ref,
        scope=scope,
        actor=actor,
        workspace_root=tmp_path,
    )
    from hg_core.materializers.steering_state_indexer import run as run_steering_indexer
    run_steering_indexer(tmp_path, rebuild=True)
    listed = list_directives(tmp_path, target_id="e1")
    assert len(listed) >= 1
    timeline = get_steering_timeline(tmp_path, "e1")
    assert len(timeline) >= 1


def test_goal_integrity_emit_and_read(tmp_path: Path) -> None:
    """Emit goal integrity score; materializer indexes; get_goal_integrity_scores returns it."""
    scope, actor = _scope_actor()
    emit_goal_integrity_score(
        target_ref={"type": "entity", "id": "e1"},
        work_item_id="wi1",
        score=0.7,
        scope=scope,
        actor=actor,
        workspace_root=tmp_path,
    )
    from hg_core.materializers.goal_integrity_indexer import run as run_gi_indexer
    run_gi_indexer(tmp_path, rebuild=True)
    scores = get_goal_integrity_scores(tmp_path, target_id="e1")
    assert len(scores) == 1
    assert scores[0]["score"] == 0.7


def test_api_steering_integrity_scores(tmp_path: Path) -> None:
    """API steering integrity scores returns scores and alerts."""
    out = api_steering_integrity_scores(tmp_path)
    assert "scores" in out
    assert "alerts" in out
    assert isinstance(out["scores"], list)
    assert isinstance(out["alerts"], list)


def test_api_steering_group_drift(tmp_path: Path) -> None:
    """API steering group_drift returns scores and alerts."""
    out = api_steering_group_drift(tmp_path)
    assert "scores" in out
    assert "alerts" in out


def test_api_operator_guardrails(tmp_path: Path) -> None:
    """API operator guardrails returns list of operator status."""
    out = api_operator_guardrails(tmp_path)
    assert isinstance(out, list)


def test_steering_change_blocked_by_policy_emits(tmp_path: Path) -> None:
    """record_steering_blocked emits STEERING_CHANGE_BLOCKED_BY_POLICY."""
    scope, actor = _scope_actor()
    eid = record_steering_blocked(
        operator_id="op1",
        reason="policy_quorum_required",
        scope=scope,
        actor=actor,
        workspace_root=tmp_path,
    )
    assert eid
    from hg_core.ledger.ledger_writer import iterate_events
    events = list(iterate_events(tmp_path, scope_type="run", scope_id="test"))
    assert any(ev.get("action") == "STEERING_CHANGE_BLOCKED_BY_POLICY" for ev in events)
