"""
Differentiators Pack 2: Reality gap, counterfactuals, governance load shaping.

See .cursor/plans/differentiators/chapter2/differentiators_pack2_reality_gap_counterfactuals/
"""

from __future__ import annotations

from pathlib import Path

from hg_core.gap import (
    compute_gap_score,
    raise_gap_alert,
    apply_gap_control,
    get_gap_scores,
)
from hg_core.counterfactuals import (
    record_counterfactual_branch,
    record_counterfactual_prediction,
    compute_regret,
    publish_counterfactual_lesson,
)
from hg_core.governance import (
    rank_approval_queue_with_gap,
    create_approval_batch,
    record_approval_batch_approved,
    record_fatigue_limit_reached,
    request_audit_spotcheck,
    record_audit_spotcheck_completed,
)
from hg_core.ledger import emit


SCOPE = {"type": "run", "id": "test_diff2"}
ACTOR = {"agent_id": "agent_diff2", "pubkey": "0" * 64, "key_id": "k"}


def test_gap_score_deterministic_given_fixed_inputs(tmp_path: Path) -> None:
    """Gap score is deterministic given fixed inputs."""
    score1, _ = compute_gap_score(
        subject_type="agent",
        subject_id="ag1",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
        prediction_error=0.2,
        verifier_disagreement=0.1,
        anomaly_rate=0.0,
        override_rate=0.0,
        tool_failure_rate=0.0,
    )
    score2, _ = compute_gap_score(
        subject_type="agent",
        subject_id="ag1",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
        prediction_error=0.2,
        verifier_disagreement=0.1,
        anomaly_rate=0.0,
        override_rate=0.0,
        tool_failure_rate=0.0,
    )
    assert 0 <= score1 <= 1
    assert score1 == score2


def test_verifier_disagreement_increases_gap_score(tmp_path: Path) -> None:
    """Verifier disagreement increases gap score."""
    score_low, _ = compute_gap_score(
        subject_type="tool",
        subject_id="t1",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
        verifier_disagreement=0.0,
        prediction_error=0.1,
    )
    score_high, _ = compute_gap_score(
        subject_type="tool",
        subject_id="t2",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
        verifier_disagreement=0.9,
        prediction_error=0.1,
    )
    assert score_high >= score_low


def test_gap_alert_triggers_control_and_rationale(tmp_path: Path) -> None:
    """Gap alert triggers control application and logs rationale."""
    compute_gap_score(
        subject_type="work_item",
        subject_id="wi1",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
        prediction_error=0.5,
    )
    scores = get_gap_scores(tmp_path, subject_id="wi1", limit=1)
    assert len(scores) >= 1
    gap_id = scores[0]["gap_id"]
    ev_alert = raise_gap_alert(
        gap_id=gap_id,
        threshold=0.3,
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
        recommended_controls=["tighten_approvals", "increase_verifier_diversity"],
    )
    assert ev_alert
    rationale_path = tmp_path / "artifacts" / "gap" / "control_rationale.json"
    rationale_path.parent.mkdir(parents=True, exist_ok=True)
    rationale_path.write_text('{"gap_id": "' + gap_id + '", "reason": "test"}', encoding="utf-8")
    ev_control = apply_gap_control(
        gap_id=gap_id,
        controls_applied=["tighten_approvals"],
        rationale_artifact_id=str(rationale_path),
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert ev_control


def test_branches_recorded_at_decision_proposal_time(tmp_path: Path) -> None:
    """Counterfactual branches recorded at decision proposal time."""
    branch_id = record_counterfactual_branch(
        decision_id="dec1",
        option_id="opt_a",
        option_summary="Alternative A",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert branch_id.startswith("cfb_")
    record_counterfactual_prediction(
        branch_id=branch_id,
        decision_id="dec1",
        prediction_id="pred1",
        expected_outcome={"value": 0.8},
        confidence=0.9,
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert (tmp_path / "artifacts" / "counterfactuals" / "branches" / f"{branch_id}.json").exists()


def test_regret_computed_and_lesson_published(tmp_path: Path) -> None:
    """Regret computed after evaluation and lesson artifact published."""
    branch_id = record_counterfactual_branch(
        decision_id="dec2",
        option_id="opt_b",
        option_summary="B",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    score, ev_regret, regret_id = compute_regret(
        decision_id="dec2",
        baseline_branch_id=branch_id,
        actual_outcome={"value": 0.3},
        predicted_best_outcome={"value": 0.9},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert ev_regret
    assert regret_id
    regret_artifacts = list((tmp_path / "artifacts" / "counterfactuals" / "regret").glob("*.json"))
    assert len(regret_artifacts) >= 1
    ev_lesson = publish_counterfactual_lesson(
        decision_id="dec2",
        regret_id=regret_id,
        lesson_summary="Prefer higher-confidence option when gap is low",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert ev_lesson
    assert (tmp_path / "artifacts" / "counterfactuals" / "lessons").exists()


def test_ranking_respects_risk_and_gap_score(tmp_path: Path) -> None:
    """Governance load: ranking respects risk budget and gap score."""
    items = [
        {"id": "i1", "risk_score": 0.5},
        {"id": "i2", "risk_score": 0.3},
    ]
    gap_scores = {"i1": 0.2, "i2": 0.8}
    ranked, event_id = rank_approval_queue_with_gap(
        items,
        gap_scores_by_item_id=gap_scores,
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert event_id
    # i2 has risk 0.3 + gap 0.8 = 1.1; i1 has 0.5 + 0.2 = 0.7 -> i2 first
    assert ranked[0]["id"] == "i2"
    assert ranked[1]["id"] == "i1"


def test_batching_emits_events_and_preserves_auditability(tmp_path: Path) -> None:
    """Batching emits correct events and preserves auditability."""
    items = [{"id": "b1", "risk_score": 0.1}]
    batch_id, ev_created = create_approval_batch(
        items=items,
        scope=SCOPE,
        actor=ACTOR,
        rationale="Low-risk batch",
        workspace_root=tmp_path,
    )
    assert batch_id
    assert ev_created
    ev_approved = record_approval_batch_approved(
        batch_id=batch_id,
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert ev_approved
    assert (tmp_path / "artifacts" / "governance" / "batches" / f"{batch_id}.json").exists()


def test_fatigue_throttles_enforced_and_logged(tmp_path: Path) -> None:
    """Fatigue throttles enforced and logged."""
    ev = record_fatigue_limit_reached(
        operator_id="op1",
        window_minutes=60,
        approvals_in_window=50,
        limit=40,
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert ev
    _ev_id, spotcheck_id = request_audit_spotcheck(
        target_id="dec1",
        reason="fatigue_trigger",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert spotcheck_id
    record_audit_spotcheck_completed(
        spotcheck_id=spotcheck_id,
        outcome="pass",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
