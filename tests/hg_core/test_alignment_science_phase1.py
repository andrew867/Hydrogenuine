"""
Layer 9 Phase 1: Schema validation tests for Alignment Science & Safety Research.
"""
import pytest

from hg_core.alignment_science import (
    process_audit_result,
    attribution_result,
    memorization_result,
    regurgitation_vs_learned_result,
    debate_outcome,
    debate_turn,
    eval_case,
    eval_run_result,
    magnification_result,
    scenario_tag,
    evidence_bundle,
    policy_briefing,
    validate_process_audit_result,
    validate_attribution_result,
    validate_memorization_result,
    validate_regurgitation_vs_learned_result,
    validate_debate_outcome,
    validate_eval_case,
    validate_eval_run_result,
    validate_magnification_result,
    validate_scenario_tag,
    validate_evidence_bundle,
    validate_policy_briefing,
)


# --- ProcessAuditResult ---


def test_process_audit_result_builder_shape() -> None:
    r = process_audit_result("dec-1", 0.85, True, "art://audit/1")
    assert r["decision_id"] == "dec-1"
    assert r["process_compliance_score"] == 0.85
    assert r["legible"] is True
    assert r["artifact_ref"] == "art://audit/1"
    assert "created_at" in r


def test_validate_process_audit_result_valid() -> None:
    r = process_audit_result("dec-1", 0.5, False, "ref")
    assert validate_process_audit_result(r) is True


def test_validate_process_audit_result_invalid_missing_field() -> None:
    assert validate_process_audit_result({"decision_id": "d", "legible": True}) is False


def test_validate_process_audit_result_invalid_wrong_type() -> None:
    assert validate_process_audit_result({"decision_id": "d", "process_compliance_score": "x", "legible": True, "artifact_ref": "r"}) is False
    assert validate_process_audit_result({"decision_id": "d", "process_compliance_score": 0.5, "legible": "yes", "artifact_ref": "r"}) is False


def test_validate_process_audit_result_not_dict() -> None:
    assert validate_process_audit_result([]) is False


# --- AttributionResult ---


def test_attribution_result_builder_shape() -> None:
    r = attribution_result("dec-1", [{"ref": "r1", "type": "event", "weight_or_rank": 1}], "art://attr/1")
    assert r["decision_id"] == "dec-1"
    assert len(r["influential_inputs"]) == 1
    assert validate_attribution_result(r) is True


def test_validate_attribution_result_invalid() -> None:
    assert validate_attribution_result({"decision_id": "d"}) is False
    assert validate_attribution_result({"decision_id": "d", "influential_inputs": "not-list", "artifact_ref": "r"}) is False


# --- MemorizationResult ---


def test_memorization_result_builder_shape() -> None:
    r = memorization_result("dec-1", True, "art://mem/1", score=0.9)
    assert r["is_memorized"] is True
    assert validate_memorization_result(r) is True


def test_validate_memorization_result_invalid() -> None:
    assert validate_memorization_result({"decision_id": "d", "is_memorized": "yes", "artifact_ref": "r"}) is False


# --- RegurgitationVsLearnedResult ---


def test_regurgitation_vs_learned_result_builder_shape() -> None:
    r = regurgitation_vs_learned_result("dec-1", "learned", "art://reg/1")
    assert r["label"] == "learned"
    assert validate_regurgitation_vs_learned_result(r) is True


def test_validate_regurgitation_vs_learned_result_invalid_label() -> None:
    assert validate_regurgitation_vs_learned_result({"decision_id": "d", "label": "unknown", "artifact_ref": "r"}) is False


# --- DebateOutcome ---


def test_debate_outcome_builder_shape() -> None:
    r = debate_outcome("sess-1", "Topic?", "draw", "art://debate/1", turns=[debate_turn("a", "content")])
    assert r["session_id"] == "sess-1"
    assert r["judge_outcome"] == "draw"
    assert len(r["turns"]) == 1
    assert validate_debate_outcome(r) is True


def test_validate_debate_outcome_invalid() -> None:
    assert validate_debate_outcome({"session_id": "s", "topic": "t", "artifact_ref": "r"}) is False  # missing judge_outcome


# --- EvalCase ---


def test_eval_case_builder_shape() -> None:
    c = eval_case("case-1", "input", "expected", domain="safety")
    assert c["case_id"] == "case-1"
    assert validate_eval_case(c) is True


def test_validate_eval_case_invalid() -> None:
    assert validate_eval_case({"case_id": "c"}) is False


# --- EvalRunResult ---


def test_eval_run_result_builder_shape() -> None:
    r = eval_run_result("run-1", ["c1"], {"c1": 1.0}, "art://eval/1", aggregate=1.0)
    assert r["eval_run_id"] == "run-1"
    assert validate_eval_run_result(r) is True


def test_validate_eval_run_result_invalid() -> None:
    assert validate_eval_run_result({"eval_run_id": "r", "case_ids": "not-list", "scores": {}, "artifact_ref": "a"}) is False


# --- MagnificationResult ---


def test_magnification_result_builder_shape() -> None:
    r = magnification_result("mag-1", "art://human", "art://magnified")
    assert r["magnification_id"] == "mag-1"
    assert validate_magnification_result(r) is True


def test_validate_magnification_result_invalid() -> None:
    assert validate_magnification_result({"magnification_id": "m"}) is False


# --- ScenarioTag ---


def test_scenario_tag_builder_shape() -> None:
    r = scenario_tag("tag-1", "pessimistic", ["ev-1"])
    assert r["scenario"] == "pessimistic"
    assert validate_scenario_tag(r) is True


def test_validate_scenario_tag_invalid_scenario() -> None:
    assert validate_scenario_tag({"tag_id": "t", "scenario": "invalid", "evidence_refs": []}) is False


# --- EvidenceBundle ---


def test_evidence_bundle_builder_shape() -> None:
    r = evidence_bundle("bundle-1", "alignment_sufficient", ["art/1"])
    assert r["type"] == "alignment_sufficient"
    assert validate_evidence_bundle(r) is True


def test_validate_evidence_bundle_invalid_type() -> None:
    assert validate_evidence_bundle({"bundle_id": "b", "type": "other", "artifact_refs": []}) is False


# --- PolicyBriefing ---


def test_policy_briefing_builder_shape() -> None:
    r = policy_briefing("brief-1", "Summary text")
    assert r["briefing_id"] == "brief-1"
    assert validate_policy_briefing(r) is True


def test_validate_policy_briefing_invalid() -> None:
    assert validate_policy_briefing({"briefing_id": "b"}) is False
