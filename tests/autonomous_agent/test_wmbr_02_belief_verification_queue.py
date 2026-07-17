"""WMBR-02 / CAGI-43 belief-conflict and evidence-verification queue tests.

Doctrine: Every model is a compressed civilization artifact.
A spectroscopy artifact is not a belief. A verification task is not an action.
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from hg_runtime.belief_verification_queue.artifact_writer import build_queue, secret_scan
from hg_runtime.belief_verification_queue.evidence_policy import build_evidence_policy_receipts
from hg_runtime.belief_verification_queue.fixtures import (
    fixture_matrix_bundle,
    tool_authorization_laundering_attempt,
    truth_laundering_attempt,
)
from hg_runtime.belief_verification_queue.gate import validate_wmbr02_gate
from hg_runtime.belief_verification_queue.matrix_loader import (
    BeliefVerificationQueueError,
    discover_latest_bundle,
    load_matrix_bundle,
    validate_matrix_bundle,
)
from hg_runtime.belief_verification_queue.priority import compute_priority
from hg_runtime.belief_verification_queue.replay import replay_queue
from hg_runtime.belief_verification_queue.schemas import (
    PHASE19_VERDICT,
    PHASE24_STATUS,
    RUNTIME_P42_VERDICT_GREEN,
    VERDICT_GREEN,
    WMBR_01A_VERDICT_GREEN,
    assert_neutral,
    BeliefVerificationQueueError as SchemaError,
)

ROOT = Path(__file__).resolve().parents[2]
WMBR_01A_PROOF_ROOT = ROOT / "docs/proofs/autonomous_agent_zero/WMBR-01A-CROSS-MODEL-PERSPECTIVE"


def _out():
    return build_queue(fixture_matrix_bundle())


def _gate_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "wmbr01a_green": True,
        "runtime_p42_green": True,
        "input_matrix_loaded": True,
        "perspective_matrix_present": True,
        "divergence_matrix_present": True,
        "candidate_claims_written": True,
        "claim_count": 20,
        "belief_conflicts_written": True,
        "conflict_count": 16,
        "verification_tasks_written": True,
        "verification_task_count": 16,
        "verification_queue_manifest_written": True,
        "evidence_policy_receipts_written": True,
        "all_claims_unverified": True,
        "all_belief_status_not_promoted": True,
        "all_tasks_queued_not_authorized": True,
        "model_output_is_not_evidence": True,
        "model_consensus_is_not_evidence": True,
        "model_refusal_is_not_evidence": True,
        "conflict_record_is_not_evidence": True,
        "verification_task_is_not_action": True,
        "source_request_is_not_external_call": True,
        "phase19_yellow_preserved": True,
        "phase40_repair_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_queue_hash": True,
        "proof_bundle_valid": True,
        "report_present": True,
        "fake_green_verified_truth_rejected": True,
        "candidate_agi_parent_phase_completed": False,
    }
    data.update(overrides)
    return data


# --- Loading ---------------------------------------------------------------

def test_wmbr02_loads_wmbr01a_artifacts():
    bundle_dir = discover_latest_bundle(WMBR_01A_PROOF_ROOT)
    assert bundle_dir is not None
    bundle = load_matrix_bundle(bundle_dir)
    validate_matrix_bundle(bundle)
    assert bundle["perspective_matrix"]["cells"]


def test_wmbr02_accepts_fixture_matrix_when_bundle_unavailable():
    assert _out()["summary"]["claim_count"] > 0


def test_wmbr02_rejects_missing_perspective_matrix():
    bundle = fixture_matrix_bundle()
    bundle["perspective_matrix"] = {"cells": []}
    with pytest.raises(BeliefVerificationQueueError):
        validate_matrix_bundle(bundle)


def test_wmbr02_rejects_missing_divergence_matrix():
    bundle = fixture_matrix_bundle()
    bundle["divergence_matrix"] = {}
    with pytest.raises(BeliefVerificationQueueError):
        validate_matrix_bundle(bundle)


# --- Claims ----------------------------------------------------------------

def test_wmbr02_extracts_candidate_claims():
    assert _out()["claims"]


def test_wmbr02_all_claims_unverified():
    assert all(c["truth_status"] == "UNVERIFIED" for c in _out()["claims"])


def test_wmbr02_no_claim_marked_true():
    assert all(c["truth_status"] != "VERIFIED_TRUE" and not c.get("claim_marked_true") for c in _out()["claims"])


def test_wmbr02_no_claim_marked_false():
    assert all(c["truth_status"] != "VERIFIED_FALSE" and not c.get("claim_marked_false") for c in _out()["claims"])


def test_wmbr02_belief_status_not_promoted():
    assert all(c["belief_status"] == "NOT_PROMOTED" for c in _out()["claims"])


# --- Conflict detection ----------------------------------------------------

def _conflict_types():
    return {c["conflict_type"] for c in _out()["conflicts"]}


def test_wmbr02_detects_unsourced_consensus():
    assert "UNSOURCED_CONSENSUS" in _conflict_types()


def test_wmbr02_detects_factual_divergence():
    assert "FACTUAL_DIVERGENCE" in _conflict_types()


def test_wmbr02_detects_refusal_divergence():
    assert "REFUSAL_DIVERGENCE" in _conflict_types()


def test_wmbr02_detects_omission_divergence():
    assert "OMISSION_DIVERGENCE" in _conflict_types()


def test_wmbr02_detects_moral_conflict():
    assert "MORAL_CONFLICT" in _conflict_types()


def test_wmbr02_detects_framing_divergence():
    assert "FRAMING_DIVERGENCE" in _conflict_types()


def test_wmbr02_conflict_record_is_not_evidence():
    assert all(not c["truth_resolved"] and not c["conflict_record_treated_as_evidence"] for c in _out()["conflicts"])


# --- Verification tasks ----------------------------------------------------

def test_wmbr02_verification_task_is_not_action():
    assert all(not t["action_authorized"] and not t["verification_task_treated_as_action"] for t in _out()["verification_tasks"])


def test_wmbr02_queue_does_not_authorize_tools():
    out = _out()
    assert all(not t["tool_authorized"] for t in out["verification_tasks"])
    assert out["queue_manifest"]["all_tasks_unauthorized"] is True


def test_wmbr02_source_request_is_not_external_call():
    assert all(not t["external_call_authorized"] and not t["source_request_treated_as_external_call"] for t in _out()["verification_tasks"])


def test_wmbr02_verification_tasks_queued_not_authorized():
    assert all(t["task_status"] == "QUEUED_NOT_AUTHORIZED" for t in _out()["verification_tasks"])


def test_wmbr02_priority_is_deterministic():
    out1 = build_queue(fixture_matrix_bundle())
    out2 = build_queue(fixture_matrix_bundle())
    assert [t["priority"] for t in out1["verification_tasks"]] == [t["priority"] for t in out2["verification_tasks"]]
    sample = out1["conflicts"][0]
    assert compute_priority(sample) == compute_priority(sample)


# --- Evidence policy -------------------------------------------------------

def test_wmbr02_evidence_policy_rejects_model_output_as_evidence():
    assert all(not p["model_output_is_evidence"] for p in _out()["evidence_policies"])


def test_wmbr02_evidence_policy_rejects_model_consensus_as_evidence():
    assert all(not p["model_consensus_is_evidence"] for p in _out()["evidence_policies"])


def test_wmbr02_evidence_policy_rejects_model_refusal_as_evidence():
    policies = build_evidence_policy_receipts(["FACTUAL", "MORAL"])
    assert all(not p["model_refusal_is_evidence"] for p in policies)


# --- Boundaries ------------------------------------------------------------

def test_wmbr02_no_web_browse():
    assert _out()["queue_manifest"]["web_browse_performed"] is False


def test_wmbr02_no_external_provider_calls():
    assert _out()["queue_manifest"]["external_provider_calls_made"] is False


def test_wmbr02_no_live_effects():
    assert _out()["queue_manifest"]["live_external_side_effects_created"] is False


def test_wmbr02_no_authority_granted():
    assert _out()["queue_manifest"]["authority_granted"] is False


def test_wmbr02_no_tools_authorized():
    assert _out()["queue_manifest"]["tools_authorized"] is False


def test_wmbr02_preserves_phase19_yellow():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")


def test_wmbr02_preserves_phase40_repair():
    assert _gate_summary()["phase40_repair_preserved"] is True


def test_wmbr02_preserves_phase24_infrastructure_only():
    assert PHASE24_STATUS == "infrastructure_only"


def test_wmbr02_does_not_complete_wmbr01_parent():
    assert validate_wmbr02_gate(_gate_summary(candidate_agi_parent_phase_completed=True))["ok"] is False


# --- Replay & laundering ---------------------------------------------------

def test_wmbr02_replay_preserves_queue_hash():
    out = _out()
    assert replay_queue(out["verification_tasks"], out["queue_manifest"])["ok"] is True


def test_wmbr02_replay_rejects_mutated_task():
    out = _out()
    tasks = copy.deepcopy(out["verification_tasks"])
    tasks[0]["priority"] = 999999
    assert replay_queue(tasks, out["queue_manifest"])["ok"] is False


def test_wmbr02_no_secret_material_in_artifacts():
    assert secret_scan(_out()) is True
    assert "sk-lm-" not in repr(_out())


def test_wmbr02_truth_laundering_attempt_rejected():
    with pytest.raises(SchemaError):
        assert_neutral(truth_laundering_attempt())


def test_wmbr02_tool_authorization_laundering_attempt_rejected():
    with pytest.raises(SchemaError):
        assert_neutral(tool_authorization_laundering_attempt())


def test_wmbr02_fake_green_verified_truth_rejected():
    assert validate_wmbr02_gate(_gate_summary(claims_marked_true=True))["ok"] is False


# --- Gate ------------------------------------------------------------------

def test_wmbr02_gate_requires_wmbr01a_green():
    assert validate_wmbr02_gate(_gate_summary(wmbr01a_green=False))["ok"] is False
    assert WMBR_01A_VERDICT_GREEN.startswith("GREEN_WMBR_01A")


def test_wmbr02_gate_requires_runtime_p42_green():
    assert validate_wmbr02_gate(_gate_summary(runtime_p42_green=False))["ok"] is False
    assert RUNTIME_P42_VERDICT_GREEN.startswith("GREEN_PHASE42")


def test_wmbr02_gate_refuses_without_claims():
    assert validate_wmbr02_gate(_gate_summary(candidate_claims_written=False, claim_count=0))["ok"] is False


def test_wmbr02_gate_refuses_without_conflicts():
    assert validate_wmbr02_gate(_gate_summary(belief_conflicts_written=False, conflict_count=0))["ok"] is False


def test_wmbr02_gate_refuses_without_verification_tasks():
    assert validate_wmbr02_gate(_gate_summary(verification_tasks_written=False, verification_task_count=0))["ok"] is False


def test_wmbr02_gate_refuses_if_claim_marked_true():
    assert validate_wmbr02_gate(_gate_summary(claims_marked_true=True))["ok"] is False


def test_wmbr02_gate_refuses_if_claim_marked_false():
    assert validate_wmbr02_gate(_gate_summary(claims_marked_false=True))["ok"] is False


def test_wmbr02_gate_refuses_if_belief_promoted():
    assert validate_wmbr02_gate(_gate_summary(belief_promoted=True))["ok"] is False


def test_wmbr02_gate_refuses_if_task_authorizes_tool():
    assert validate_wmbr02_gate(_gate_summary(verification_tasks_authorize_tools=True))["ok"] is False


def test_wmbr02_gate_refuses_if_external_call_made():
    assert validate_wmbr02_gate(_gate_summary(external_provider_calls_made=True))["ok"] is False


def test_wmbr02_gate_refuses_if_authority_granted():
    assert validate_wmbr02_gate(_gate_summary(authority_granted=True))["ok"] is False


def test_wmbr02_gate_refuses_if_live_effect_created():
    assert validate_wmbr02_gate(_gate_summary(live_external_side_effects_created=True))["ok"] is False


def test_wmbr02_gate_refuses_without_proof_bundle():
    assert validate_wmbr02_gate(_gate_summary(proof_bundle_valid=False))["ok"] is False


def test_wmbr02_gate_passes_on_full_summary():
    assert validate_wmbr02_gate(_gate_summary())["ok"] is True
