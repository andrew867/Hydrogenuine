"""
Ch3 Metacognition: self-assessment, tool outcomes, capability profile, postmortem, calibration, proof-path.
See .cursor/plans/stickyreality/chapter3/self_awareness_metacognition/
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from hg_core.metacognition import (
    record_self_assessment,
    record_tool_outcome,
    publish_capability_profile,
    record_postmortem,
    get_proof_path,
    export_proof_path,
    list_self_assessments,
    get_calibration_metrics,
    get_tool_reliability,
    check_has_self_assessment,
)
from hg_core.ledger import emit
from hg_core.ledger.ledger_writer import iter_events_by_scope
from hg_core.materializers.metacognition_metrics import run as run_metacognition_metrics


SCOPE = {"type": "run", "id": "test_run"}
ACTOR = {"agent_id": "test", "pubkey": "0" * 64, "key_id": "k"}


def test_self_assessment_emits_event_and_rationale(tmp_path: Path):
    """record_self_assessment emits SELF_ASSESSMENT_RECORDED and writes rationale artifact."""
    aid = record_self_assessment(
        decision_id="dec_1",
        scope=SCOPE,
        actor=ACTOR,
        confidence=0.7,
        uncertainty_factors=["missing_data"],
        risk_flags=[],
        recommended_controls={"require_approval": True, "slow_mode": False},
        workspace_root=tmp_path,
    )
    assert aid
    evs = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "SELF_ASSESSMENT_RECORDED" for _, _, ev in evs)
    payload = next(ev["payload"] for _, _, ev in evs if ev.get("action") == "SELF_ASSESSMENT_RECORDED")
    assert payload["decision_id"] == "dec_1"
    assert payload["confidence"] == 0.7
    assert payload["recommended_controls"]["require_approval"] is True
    assert (tmp_path / "artifacts" / "metacognition" / "self_assessment").exists()


def test_tool_outcome_emits_event(tmp_path: Path):
    """record_tool_outcome emits TOOL_OUTCOME_RECORDED with outcome, latency, error_class."""
    rid = record_tool_outcome(
        tool_call_id="tc_1",
        tool_name="http_get",
        inputs_hash="abc",
        scope=SCOPE,
        actor=ACTOR,
        outcome="success",
        latency_ms=100,
        error_class=None,
        workspace_root=tmp_path,
    )
    assert rid
    evs = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "TOOL_OUTCOME_RECORDED" for _, _, ev in evs)
    payload = next(ev["payload"] for _, _, ev in evs if ev.get("action") == "TOOL_OUTCOME_RECORDED")
    assert payload["tool_name"] == "http_get"
    assert payload["outcome"] == "success"
    assert payload["latency_ms"] == 100


def test_tool_outcome_with_summary_artifact(tmp_path: Path):
    """record_tool_outcome with summary writes artifact and includes in artifact_links."""
    record_tool_outcome(
        tool_call_id="tc_2",
        tool_name="shell",
        inputs_hash="x",
        scope=SCOPE,
        actor=ACTOR,
        outcome="fail",
        latency_ms=50,
        error_class="TimeoutError",
        summary={"error": "timeout"},
        workspace_root=tmp_path,
    )
    evs = list(iter_events_by_scope(tmp_path))
    payload = next(ev["payload"] for _, _, ev in evs if ev.get("action") == "TOOL_OUTCOME_RECORDED" and ev["payload"].get("tool_call_id") == "tc_2")
    assert len(payload.get("artifact_links", [])) >= 1


def test_capability_profile_published(tmp_path: Path):
    """publish_capability_profile writes YAML and emits CAPABILITY_PROFILE_PUBLISHED."""
    profile = {
        "agent_key_id": "kid1",
        "last_updated": "2026-02-24T12:00:00Z",
        "tools": [
            {"name": "http_get", "allowed": True, "expected_latency_ms": 500, "expected_failure_rate": 0.05},
        ],
    }
    aid = publish_capability_profile(
        agent_key_id="kid1",
        profile=profile,
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert aid
    assert (tmp_path / "artifacts" / "capabilities" / "kid1" / "capability_profile.yaml").exists()
    evs = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "CAPABILITY_PROFILE_PUBLISHED" for _, _, ev in evs)


def test_postmortem_published(tmp_path: Path):
    """record_postmortem emits POSTMORTEM_PUBLISHED and writes artifact."""
    pid = record_postmortem(
        related_event_ids=["e1"],
        related_decision_ids=["d1"],
        root_cause_tags=["config_error"],
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert pid
    evs = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "POSTMORTEM_PUBLISHED" for _, _, ev in evs)


def test_materializer_calibration_and_tool_reliability(tmp_path: Path):
    """Metacognition materializer produces calibration and tool_reliability; API returns them."""
    record_self_assessment(
        decision_id="dec_a",
        scope=SCOPE,
        actor=ACTOR,
        confidence=0.8,
        uncertainty_factors=[],
        risk_flags=[],
        recommended_controls={"require_approval": False, "slow_mode": False},
        workspace_root=tmp_path,
    )
    record_tool_outcome(
        tool_call_id="t1", tool_name="fetch", inputs_hash="h", scope=SCOPE, actor=ACTOR,
        outcome="success", latency_ms=10, workspace_root=tmp_path,
    )
    record_tool_outcome(
        tool_call_id="t2", tool_name="fetch", inputs_hash="h", scope=SCOPE, actor=ACTOR,
        outcome="fail", latency_ms=5, workspace_root=tmp_path,
    )
    emit(
        "PREDICTION_MADE",
        "prediction", "pred_1",
        {"prediction_id": "pred_1", "decision_id": "dec_a", "confidence": 0.9},
        scope=SCOPE, actor=ACTOR, workspace_root=tmp_path,
    )
    emit(
        "EVALUATION_RECORDED",
        "evaluation", "eval_1",
        {"evaluation_id": "eval_1", "prediction_id": "pred_1", "score": {"success": True}},
        scope=SCOPE, actor=ACTOR, workspace_root=tmp_path,
    )
    run_metacognition_metrics(tmp_path, rebuild=True)
    root = tmp_path / "memory" / "materialized"
    assert (root / "self_assessments.jsonl").exists()
    assert (root / "tool_reliability.jsonl").exists()
    assert (root / "calibration_timeseries.jsonl").exists()
    assert (root / "calibration_curve.jsonl").exists()
    cal = get_calibration_metrics(tmp_path)
    assert "calibration_timeseries" in cal
    assert "calibration_curve" in cal
    assert "mean_brier_score" in cal
    rel = get_tool_reliability(tmp_path)
    assert len(rel) >= 1
    assert any(r.get("tool_name") == "fetch" for r in rel)
    assessments = list_self_assessments(tmp_path)
    assert len(assessments) == 1
    assert assessments[0]["decision_id"] == "dec_a"


def test_proof_path_and_export(tmp_path: Path):
    """get_proof_path returns decision/predictions/evaluations/self_assessments; export emits DECISION_AUDIT_EXPORTED."""
    emit(
        "DECISION_COMMITTED",
        "decision", "dec_p",
        {"decision_id": "dec_p", "title": "Test", "based_on_claim_ids": [], "value_weights": [], "context_ref": {}, "produced_artifact_ids": []},
        scope=SCOPE, actor=ACTOR, workspace_root=tmp_path,
    )
    record_self_assessment(
        decision_id="dec_p",
        scope=SCOPE,
        actor=ACTOR,
        confidence=0.6,
        uncertainty_factors=[],
        risk_flags=[],
        recommended_controls={"require_approval": False, "slow_mode": False},
        workspace_root=tmp_path,
    )
    run_metacognition_metrics(tmp_path, rebuild=True)
    proof = get_proof_path(tmp_path, "dec_p")
    assert proof["decision_id"] == "dec_p"
    assert "decision" in proof
    assert "self_assessments" in proof
    assert len(proof["self_assessments"]) == 1
    out = export_proof_path(tmp_path, "dec_p", scope=SCOPE, actor=ACTOR)
    assert "artifact_path" in out
    assert "event_id" in out
    assert (tmp_path / "artifacts" / "metacognition" / "audit").exists()
    evs = list(iter_events_by_scope(tmp_path))
    assert any(ev.get("action") == "DECISION_AUDIT_EXPORTED" for _, _, ev in evs)


def test_check_has_self_assessment(tmp_path: Path):
    """check_has_self_assessment returns True after assessment for decision_id, False otherwise."""
    assert check_has_self_assessment(tmp_path, "dec_any") is False
    record_self_assessment(
        decision_id="dec_any",
        scope=SCOPE,
        actor=ACTOR,
        confidence=0.5,
        uncertainty_factors=[],
        risk_flags=[],
        recommended_controls={"require_approval": False, "slow_mode": False},
        workspace_root=tmp_path,
    )
    run_metacognition_metrics(tmp_path, rebuild=True)
    assert check_has_self_assessment(tmp_path, "dec_any") is True
    assert check_has_self_assessment(tmp_path, "other_dec") is False


def test_self_assessment_cannot_directly_raise_trust(tmp_path: Path):
    """Safety: SELF_ASSESSMENT_RECORDED does not trigger trust/budget change; no such logic in code."""
    record_self_assessment(
        decision_id="dec_s",
        scope=SCOPE,
        actor=ACTOR,
        confidence=1.0,
        uncertainty_factors=[],
        risk_flags=[],
        recommended_controls={"require_approval": False, "slow_mode": False},
        workspace_root=tmp_path,
    )
    evs = list(iter_events_by_scope(tmp_path))
    actions = [ev.get("action") for _, _, ev in evs]
    assert "SELF_ASSESSMENT_RECORDED" in actions
    assert "TRUST_BAND_CHANGED" not in actions
    assert "BUDGET_ADJUSTED" not in actions
