"""ORP-1 operator review decision ledger tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.operator_review_promotion.decision_ledger import (
    build_operator_review_decision_ledger,
    validate_orp1_gate,
)
from hg_runtime.operator_review_promotion.decision_replay import replay_decision_ledger
from hg_runtime.operator_review_promotion.redaction import secret_scan
from hg_runtime.operator_review_promotion.schemas import PHASE19_VERDICT, PHASE24_STATUS

ROOT = Path(__file__).resolve().parents[2]


def _layer():
    return build_operator_review_decision_ledger(ROOT)


def _summary(**overrides):
    data = {
        "verdict": "GREEN_ORP_1_OPERATOR_REVIEW_DECISION_LEDGER",
        "leb5_inputs_loaded": True,
        "leb6_inputs_loaded": True,
        "leb7_inputs_loaded": True,
        "operator_review_decisions_written": True,
        "operator_review_manifest_written": True,
        "reviewed_evidence_links_written": True,
        "operator_rejection_records_written": True,
        "operator_deferral_records_written": True,
        "ledger_is_append_only": True,
        "original_evidence_preserved": True,
        "approval_does_not_prove": True,
        "approval_does_not_authorize_action": True,
        "approval_does_not_authorize_tool": True,
        "approval_does_not_authorize_web_or_provider": True,
        "rejection_does_not_delete": True,
        "deferral_remains_open": True,
        "replay_preserves_ledger_hashes": True,
        "secret_redaction_passed": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_orp1_loads_leb_inputs():
    m = _layer()["manifest"]
    assert m["leb5_review_task_count"] > 0
    assert m["leb6_health_finding_count"] > 0
    assert m["leb7_retraction_count"] > 0


def test_orp1_ledger_is_append_only():
    assert _layer()["manifest"]["operator_review_ledger_is_append_only"] is True


def test_orp1_original_evidence_preserved():
    assert _layer()["manifest"]["original_evidence_preserved"] is True


def test_orp1_rejection_does_not_delete():
    for record in _layer()["operator_rejection_records"]:
        assert record["operator_rejection_is_deletion"] is False
        assert record["deletion_performed"] is False


def test_orp1_approval_does_not_prove_or_authorize():
    for decision in _layer()["decisions"]:
        assert decision["operator_review_is_truth"] is False
        assert decision["operator_approval_is_action_permission"] is False
        assert decision["operator_approval_authorizes_tools"] is False
        assert decision["operator_approval_authorizes_web"] is False
        assert decision["operator_approval_authorizes_providers"] is False


def test_orp1_deferral_remains_open():
    for record in _layer()["operator_deferral_records"]:
        assert record["review_remains_open"] is True
        assert record["operator_deferral_is_failure"] is False


def test_orp1_no_belief_promotion_or_live_effects():
    layer = _layer()
    assert all(not d["belief_promotion_automatic"] for d in layer["decisions"])
    assert all(not d["live_external_side_effects_created"] for d in layer["decisions"])


def test_orp1_replay_preserves_ledger_hashes():
    assert _layer()["replay"]["replay_preserves_ledger_hashes"] is True


def test_orp1_replay_rejects_mutated_decision():
    layer = _layer()
    decisions = [dict(d) for d in layer["decisions"]]
    decisions[0]["rationale"] = "mutated"
    replay = replay_decision_ledger(
        decisions,
        layer["reviewed_evidence_links"],
        layer["operator_rejection_records"],
        layer["operator_deferral_records"],
        layer["manifest"],
    )
    assert replay["replay_preserves_ledger_hashes"] is False


def test_orp1_secret_redaction_passes():
    assert secret_scan(_layer()) is True


def test_orp1_preserves_phase19_yellow():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")


def test_orp1_preserves_phase24_infrastructure_only():
    assert PHASE24_STATUS == "infrastructure_only"


def test_orp1_gate_passes_full_summary():
    assert validate_orp1_gate(_summary())["ok"] is True


def test_orp1_gate_refuses_truth_laundering():
    assert validate_orp1_gate(_summary(operator_review_treated_as_truth=True))["ok"] is False


def test_orp1_gate_refuses_action_authority():
    assert validate_orp1_gate(_summary(authority_granted=True))["ok"] is False


def test_orp1_gate_refuses_tool_authorization():
    assert validate_orp1_gate(_summary(tools_authorized=True))["ok"] is False


def test_orp1_gate_refuses_web_or_provider():
    assert validate_orp1_gate(_summary(web_authorized=True))["ok"] is False
    assert validate_orp1_gate(_summary(providers_authorized=True))["ok"] is False


def test_orp1_gate_refuses_deletion():
    assert validate_orp1_gate(_summary(deletion_performed=True))["ok"] is False


def test_orp1_gate_refuses_automatic_belief_promotion():
    assert validate_orp1_gate(_summary(belief_promotion_automatic=True))["ok"] is False


def test_orp1_gate_refuses_without_replay():
    assert validate_orp1_gate(_summary(replay_preserves_ledger_hashes=False))["ok"] is False
