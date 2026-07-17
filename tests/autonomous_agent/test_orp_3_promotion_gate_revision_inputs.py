"""ORP-3 promotion gate to local belief revision input tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.operator_review_promotion.promotion_gate_replay import replay_promotion_gate
from hg_runtime.operator_review_promotion.promotion_gate_runner import (
    build_promotion_gate_revision_inputs,
    validate_orp3_gate,
)
from hg_runtime.operator_review_promotion.redaction import secret_scan
from hg_runtime.operator_review_promotion.schemas import PHASE19_VERDICT, PHASE24_STATUS

ROOT = Path(__file__).resolve().parents[2]


def _layer():
    return build_promotion_gate_revision_inputs(ROOT)


def _summary(**overrides):
    data = {
        "verdict": "GREEN_ORP_3_PROMOTION_GATE_REVISION_INPUTS",
        "orp2_green": True,
        "promotion_gate_results_written": True,
        "promotion_gated_revision_inputs_written": True,
        "promotion_gate_manifest_written": True,
        "gate_pass_not_truth": True,
        "gate_pass_not_certainty": True,
        "gate_pass_not_action_permission": True,
        "gate_fail_not_deletion": True,
        "revision_input_not_belief_state": True,
        "no_old_proof_mutation": True,
        "no_automatic_belief_promotion": True,
        "no_authority": True,
        "no_tools": True,
        "no_live_effects": True,
        "replay_preserves_gate_hashes": True,
        "secret_redaction_passed": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_orp3_writes_promotion_gate_results():
    assert len(_layer()["promotion_gate_results"]) == 1


def test_orp3_writes_revision_inputs():
    assert len(_layer()["promotion_gated_revision_inputs"]) == 1


def test_orp3_manifest_written():
    layer = _layer()
    assert layer["manifest"]["record_type"] == "promotion_gate_manifest_v1"
    assert layer["manifest"]["revision_input_count"] == 1


def test_orp3_gate_pass_is_not_truth_or_certainty():
    gate = _layer()["promotion_gate_results"][0]
    assert gate["gate_pass_is_truth"] is False
    assert gate["gate_pass_is_certainty"] is False


def test_orp3_gate_pass_is_not_action_permission():
    gate = _layer()["promotion_gate_results"][0]
    assert gate["gate_pass_is_action_permission"] is False
    assert gate["gate_pass_authorizes_tools"] is False


def test_orp3_gate_fail_is_not_deletion():
    assert _layer()["manifest"]["gate_fail_is_deletion"] is False


def test_orp3_revision_input_is_not_belief_state():
    record = _layer()["promotion_gated_revision_inputs"][0]
    assert record["revision_input_is_belief_state"] is False
    assert record["belief_promoted"] is False


def test_orp3_no_old_proof_mutation_or_automatic_promotion():
    layer = _layer()
    records = layer["promotion_gate_results"] + layer["promotion_gated_revision_inputs"]
    assert all(not r["old_proof_mutated"] for r in records)
    assert all(not r["belief_promotion_automatic"] for r in records)


def test_orp3_no_authority_tools_live_effects():
    layer = _layer()
    records = layer["promotion_gate_results"] + layer["promotion_gated_revision_inputs"]
    assert all(not r["authority_granted"] for r in records)
    assert all(not r["tools_authorized"] for r in records)
    assert all(not r["live_external_side_effects_created"] for r in records)


def test_orp3_replay_preserves_gate_hashes():
    assert _layer()["replay"]["replay_preserves_gate_hashes"] is True


def test_orp3_replay_rejects_mutated_revision_input():
    layer = _layer()
    inputs = [dict(r) for r in layer["promotion_gated_revision_inputs"]]
    inputs[0]["revision_input_use"] = "MUTATED"
    replay = replay_promotion_gate(layer["promotion_gate_results"], inputs, layer["manifest"])
    assert replay["replay_preserves_gate_hashes"] is False


def test_orp3_secret_scan_passes():
    assert secret_scan(_layer()) is True


def test_orp3_preserves_phase19_yellow():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")


def test_orp3_preserves_phase24_infrastructure_only():
    assert PHASE24_STATUS == "infrastructure_only"


def test_orp3_gate_passes_full_summary():
    assert validate_orp3_gate(_summary())["ok"] is True


def test_orp3_gate_refuses_missing_revision_inputs():
    assert validate_orp3_gate(_summary(promotion_gated_revision_inputs_written=False))["ok"] is False


def test_orp3_gate_refuses_gate_as_truth():
    assert validate_orp3_gate(_summary(gate_pass_not_truth=False))["ok"] is False


def test_orp3_gate_refuses_revision_input_as_belief_state():
    assert validate_orp3_gate(_summary(revision_input_not_belief_state=False))["ok"] is False


def test_orp3_gate_refuses_authority_or_tools():
    assert validate_orp3_gate(_summary(authority_granted=True))["ok"] is False
    assert validate_orp3_gate(_summary(tools_authorized=True))["ok"] is False


def test_orp3_gate_refuses_old_proof_mutation():
    assert validate_orp3_gate(_summary(old_proof_mutated=True))["ok"] is False


def test_orp3_gate_refuses_without_replay():
    assert validate_orp3_gate(_summary(replay_preserves_gate_hashes=False))["ok"] is False
