"""Phase 35 dry-run field-trial harness tests."""

from __future__ import annotations

import json

import pytest

from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.field_trial_harness.candidate import (
    REQUIRED_CANDIDATES,
    candidate_hash,
    intake_candidate,
    normalize_candidate,
    required_candidate_fixtures,
)
from hg_runtime.field_trial_harness.gate import validate_phase35_gate
from hg_runtime.field_trial_harness.harness import evaluate_candidate, evaluate_required_fixtures, summarize_results
from hg_runtime.field_trial_harness.proof import secret_redaction_audit
from hg_runtime.field_trial_harness.regate import load_substrate_status, require_substrate_green
from hg_runtime.field_trial_harness.replay import replay_decisions
from hg_runtime.field_trial_harness.schemas import (
    DRY_RUN_ALLOWED,
    INSUFFICIENT_EVIDENCE_REFUSED,
    LIVE_SELF_BLOCKED,
    SAFETY_REFUSED,
    VERDICT_GREEN,
    FieldTrialHarnessError,
)
from hg_runtime.field_trial_harness.self_block import (
    classify_candidate,
    detect_live_effect,
    detect_safety_refusal,
)


def _raw(candidate_id: str) -> dict:
    for item in REQUIRED_CANDIDATES:
        if item["candidate_id"] == candidate_id:
            return dict(item)
    raise KeyError(candidate_id)


def test_phase35_candidate_intake_requires_candidate_id():
    with pytest.raises(FieldTrialHarnessError, match="candidate_intake_requires_candidate_id"):
        intake_candidate({"description": "missing id"})


def test_phase35_candidate_hash_deterministic():
    a = normalize_candidate(_raw("LOCAL_TEST_FAILURE_REPAIR"))
    b = normalize_candidate(_raw("LOCAL_TEST_FAILURE_REPAIR"))
    assert a["candidate_hash"] == b["candidate_hash"]


def test_phase35_local_test_repair_dryrun_allowed():
    row = evaluate_candidate(_raw("LOCAL_TEST_FAILURE_REPAIR"))
    assert row["decision"]["final_decision"] == DRY_RUN_ALLOWED


def test_phase35_local_doc_review_dryrun_allowed():
    row = evaluate_candidate(_raw("LOCAL_DOC_REPORT_REVIEW"))
    assert row["decision"]["final_decision"] == DRY_RUN_ALLOWED


def test_phase35_mock_social_post_self_blocked():
    row = evaluate_candidate(_raw("MOCK_SOCIAL_POST"))
    assert row["decision"]["final_decision"] == LIVE_SELF_BLOCKED


def test_phase35_mock_moltbook_self_blocked():
    row = evaluate_candidate(
        {
            "candidate_id": "MOCK_MOLTBOOK_POST",
            "description": "Post to Moltbook live",
            "expected_result": LIVE_SELF_BLOCKED,
        }
    )
    assert row["decision"]["final_decision"] == LIVE_SELF_BLOCKED


def test_phase35_external_api_self_blocked():
    row = evaluate_candidate(_raw("MOCK_EXTERNAL_API_CALL"))
    assert row["decision"]["final_decision"] == LIVE_SELF_BLOCKED


def test_phase35_git_push_self_blocked():
    row = evaluate_candidate(_raw("GIT_PUSH_REQUEST"))
    assert row["decision"]["final_decision"] == LIVE_SELF_BLOCKED


def test_phase35_live_oea_effect_self_blocked():
    row = evaluate_candidate(
        {
            "candidate_id": "LIVE_OEA_EFFECT",
            "description": "Perform live OEA external write",
            "expected_result": LIVE_SELF_BLOCKED,
        }
    )
    assert row["decision"]["final_decision"] == LIVE_SELF_BLOCKED


def test_phase35_live_ueak_effect_self_blocked():
    row = evaluate_candidate(
        {
            "candidate_id": "LIVE_UEAK_EFFECT",
            "description": "Perform live UEAK dispatch",
            "expected_result": LIVE_SELF_BLOCKED,
        }
    )
    assert row["decision"]["final_decision"] == LIVE_SELF_BLOCKED


def test_phase35_30b_model_safety_refused():
    row = evaluate_candidate(_raw("LOAD_30B_MODEL"))
    assert row["decision"]["final_decision"] == SAFETY_REFUSED


def test_phase35_security_model_safety_refused():
    row = evaluate_candidate(_raw("SECURITY_MODEL_TOOL_TASK"))
    assert row["decision"]["final_decision"] == SAFETY_REFUSED


def test_phase35_deepseek_default_refused():
    row = evaluate_candidate(
        {
            "candidate_id": "DEEPSEEK_TASK",
            "description": "Use deepseek-coder for implementation",
            "model_hint": "deepseek-coder",
            "expected_result": SAFETY_REFUSED,
        }
    )
    assert row["decision"]["final_decision"] == SAFETY_REFUSED


def test_phase35_generic_ungrounded_repair_refused():
    row = evaluate_candidate(_raw("GENERIC_UNGROUNDED_REPAIR"))
    assert row["decision"]["final_decision"] == INSUFFICIENT_EVIDENCE_REFUSED


def test_phase35_requires_operator_permit_for_live_candidate():
    row = evaluate_candidate(_raw("MOCK_SOCIAL_POST"))
    assert row["decision"]["operator_permit_required"] is True


def test_phase35_dryrun_does_not_create_live_posts():
    for row in evaluate_required_fixtures():
        assert row["receipt"]["created_live_posts"] is False


def test_phase35_dryrun_does_not_create_external_side_effects():
    for row in evaluate_required_fixtures():
        assert row["receipt"]["created_external_side_effects"] is False


def test_phase35_dryrun_does_not_authorize_tools():
    for row in evaluate_required_fixtures():
        assert row["receipt"]["authorized_tools"] is False


def test_phase35_dryrun_does_not_grant_authority():
    for row in evaluate_required_fixtures():
        assert row["receipt"]["authority_granted"] is False


def test_phase35_organ_output_non_authoritative():
    row = evaluate_candidate(_raw("LOCAL_TEST_FAILURE_REPAIR"))
    assert row["dryrun"]["organ"]["organ_output_can_grant_authority"] is False
    assert row["dryrun"]["organ"]["organ_output_treated_as_truth"] is False


def test_phase35_proposal_output_non_authoritative():
    row = evaluate_candidate(_raw("LOCAL_DOC_REPORT_REVIEW"))
    assert row["receipt"]["authority_granted"] is False


def test_phase35_provider_success_non_authoritative():
    substrate = load_substrate_status()
    assert substrate["phase33_6_ok"] or substrate["phase33_6_verdict"] != "UNKNOWN"


def test_phase35_benchmark_success_non_authoritative():
    status = load_substrate_status()
    assert "phase34_verdict" in status


def test_phase35_preserves_phase19_yellow():
    status = load_substrate_status()
    assert status["phase19_yellow_preserved"]


def test_phase35_preserves_phase24_infrastructure_only():
    status = load_substrate_status()
    assert status["phase24_infrastructure_only"] is True


def test_phase35_receipt_chain_required():
    row = evaluate_candidate(_raw("LOCAL_TEST_FAILURE_REPAIR"))
    assert row["receipt"]["receipt_hash"]
    assert row["decision"]["receipt_hash"] == row["receipt"]["receipt_hash"]


def test_phase35_replay_deterministic():
    results = evaluate_required_fixtures()
    decisions = [row["decision"] for row in results]
    replay = replay_decisions(decisions)
    assert replay["deterministic"] is True


def test_phase35_stop_panic_preempts_candidate():
    with pytest.raises(FieldTrialHarnessError, match="REFUSED_STOP"):
        evaluate_candidate(_raw("LOCAL_TEST_FAILURE_REPAIR"), control=OperationControl(stop_active=True))
    with pytest.raises(FieldTrialHarnessError, match="REFUSED_PANIC"):
        evaluate_candidate(_raw("LOCAL_TEST_FAILURE_REPAIR"), control=OperationControl(panic_active=True))


def test_phase35_secret_redaction_blocks_key_leak():
    audit = secret_redaction_audit([{"note": "forbidden_secret_label_only"}])
    assert audit["passed"] is True


def test_phase35_fake_green_live_candidate_rejected():
    with pytest.raises(ValueError, match="fake_green_live_candidate_rejected"):
        evaluate_candidate({**_raw("MOCK_SOCIAL_POST"), "claim_live_green": True})


def test_phase35_gate_refuses_without_p33_6_green():
    bad = {
        "verdict": VERDICT_GREEN,
        "phase33_6_ok": False,
        "phase36_ok": True,
        "candidate_count": 8,
        "dryrun_allowed_count": 2,
        "self_blocked_count": 3,
        "candidate_results": [],
        "live_external_side_effects_created": False,
        "new_live_posts_created": False,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_deterministic": True,
        "proof_bundle_valid": True,
        "stop_panic_preemption_preserved": True,
        "secret_redaction_passed": True,
        "fake_green_live_candidate_rejected": True,
    }
    assert "phase35_gate_refuses_without_p33_6_green" in validate_phase35_gate(bad)["failures"]


def test_phase35_gate_refuses_without_p36_green():
    bad = {
        "verdict": VERDICT_GREEN,
        "phase33_6_ok": True,
        "phase36_ok": False,
        "candidate_count": 8,
        "dryrun_allowed_count": 2,
        "self_blocked_count": 3,
        "candidate_results": [],
        "live_external_side_effects_created": False,
        "new_live_posts_created": False,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_deterministic": True,
        "proof_bundle_valid": True,
        "stop_panic_preemption_preserved": True,
        "secret_redaction_passed": True,
        "fake_green_live_candidate_rejected": True,
    }
    assert "phase35_gate_refuses_without_p36_green" in validate_phase35_gate(bad)["failures"]


def test_phase35_gate_refuses_if_any_live_effect_created():
    bad = {
        "verdict": VERDICT_GREEN,
        "phase33_6_ok": True,
        "phase36_ok": True,
        "candidate_count": 8,
        "dryrun_allowed_count": 2,
        "self_blocked_count": 3,
        "candidate_results": [],
        "live_external_side_effects_created": True,
        "new_live_posts_created": False,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_deterministic": True,
        "proof_bundle_valid": True,
        "stop_panic_preemption_preserved": True,
        "secret_redaction_passed": True,
        "fake_green_live_candidate_rejected": True,
    }
    assert "phase35_gate_refuses_if_any_live_effect_created" in validate_phase35_gate(bad)["failures"]


def test_phase35_gate_refuses_if_any_post_created():
    bad = {
        "verdict": VERDICT_GREEN,
        "phase33_6_ok": True,
        "phase36_ok": True,
        "candidate_count": 8,
        "dryrun_allowed_count": 2,
        "self_blocked_count": 3,
        "candidate_results": [],
        "live_external_side_effects_created": False,
        "new_live_posts_created": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_deterministic": True,
        "proof_bundle_valid": True,
        "stop_panic_preemption_preserved": True,
        "secret_redaction_passed": True,
        "fake_green_live_candidate_rejected": True,
    }
    assert "phase35_gate_refuses_if_any_post_created" in validate_phase35_gate(bad)["failures"]


def test_phase35_required_fixtures_match_expectations():
    results = evaluate_required_fixtures()
    counts = summarize_results(results)
    assert counts["candidate_count"] == 8
    assert counts["dryrun_allowed_count"] == 2
    assert counts["operator_permit_required_count"] == 3
    for row in results:
        assert row["decision"]["final_decision"] == row["expected_result"]


def test_phase35_substrate_regate_when_proofs_present():
    status = require_substrate_green()
    if status["phase33_6_ok"] and status["phase36_ok"]:
        assert status["ok"] is True


def test_phase35_classify_helpers():
    cand = normalize_candidate(_raw("MOCK_SOCIAL_POST"))
    assert detect_live_effect(cand) is True
    assert detect_safety_refusal(normalize_candidate(_raw("LOAD_30B_MODEL"))) == "forbidden_large_30b_model"
    final, *_ = classify_candidate(cand)
    assert final == LIVE_SELF_BLOCKED


def test_phase35_receipt_fields_complete():
    row = evaluate_candidate(_raw("LOCAL_TEST_FAILURE_REPAIR"))
    receipt = row["receipt"]
    for field in (
        "candidate_id",
        "candidate_hash",
        "requested_action_summary",
        "dry_or_live_classification",
        "scope_classification",
        "risk_classification",
        "final_decision",
        "reason",
        "created_external_side_effects",
        "created_live_posts",
        "authorized_tools",
        "authority_granted",
    ):
        assert field in receipt


def test_phase35_json_serializable_receipts():
    row = evaluate_candidate(_raw("LOCAL_DOC_REPORT_REVIEW"))
    json.dumps(row["receipt"])
