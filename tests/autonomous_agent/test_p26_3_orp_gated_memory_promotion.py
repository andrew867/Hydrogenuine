"""P26-3 ORP-gated memory promotion tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_runtime.experience_ledger.gate import validate_p26_3_gate
from hg_runtime.experience_ledger.memory_promotion_gate import decide_memory_promotion
from hg_runtime.experience_ledger.orp_memory_bridge import build_memory_promotion_request
from hg_runtime.experience_ledger.promotion_decision_ledger import build_p26_3_bridge
from hg_runtime.experience_ledger.schemas import ExperienceLedgerBoundaryError


def _summary(**overrides):
    data = {
        "verdict": "GREEN_P26_3_ORP_GATED_MEMORY_PROMOTION_BRIDGE",
        "promotion_requests_written": True,
        "promotion_decisions_written": True,
        "promotion_rejections_written": True,
        "orp_memory_bridge_manifest_written": True,
        "creates_request_from_memory_record": True,
        "request_includes_memory_id": True,
        "request_includes_provenance_pointer": True,
        "promotion_request_is_not_promotion": True,
        "orp_decision_required": True,
        "automatic_promotion_rejected": True,
        "memory_as_truth_rejected": True,
        "recall_as_authority_rejected": True,
        "missing_provenance_rejected": True,
        "quarantined_memory_review_only": True,
        "reject_decision_supported": True,
        "defer_decision_supported": True,
        "approved_for_review_without_truth_claim": True,
        "no_tool_authorization": True,
        "no_live_effects": True,
        "no_deletion": True,
        "no_orp_bypass": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_stable": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_p26_3_creates_promotion_request_from_memory_record():
    layer = build_p26_3_bridge(Path.cwd())
    assert layer["requests"][0]["record_type"] == "memory_promotion_request_v1"


def test_p26_3_request_includes_memory_id_and_provenance_pointer():
    request = build_p26_3_bridge(Path.cwd())["requests"][0]
    assert request["memory_id"]
    assert request["provenance_refs"]


def test_p26_3_promotion_request_is_not_promotion():
    request = build_p26_3_bridge(Path.cwd())["requests"][0]
    assert request["promotion_request_is_promotion"] is False


def test_p26_3_orp_decision_required():
    request = build_p26_3_bridge(Path.cwd())["requests"][0]
    assert request["operator_orp_decision_required"] is True


def test_p26_3_automatic_promotion_rejected():
    request = build_p26_3_bridge(Path.cwd())["requests"][0]
    request["promotion_request_auto_applied"] = True
    with pytest.raises(ExperienceLedgerBoundaryError):
        decide_memory_promotion(request, "APPROVED_FOR_REVIEW")


def test_p26_3_memory_as_truth_rejected():
    request = build_p26_3_bridge(Path.cwd())["requests"][0]
    request["memory_treated_as_truth"] = True
    with pytest.raises(ExperienceLedgerBoundaryError):
        decide_memory_promotion(request, "APPROVED_FOR_REVIEW")


def test_p26_3_recall_as_authority_rejected():
    request = build_p26_3_bridge(Path.cwd())["requests"][0]
    request["recall_treated_as_authority"] = True
    with pytest.raises(ExperienceLedgerBoundaryError):
        decide_memory_promotion(request, "APPROVED_FOR_REVIEW")


def test_p26_3_missing_provenance_rejected():
    memory = dict(build_p26_3_bridge(Path.cwd())["memory_records"][0])
    memory["provenance_refs"] = []
    assert build_memory_promotion_request(memory)["rejection_reason"] == "MISSING_PROVENANCE"


def test_p26_3_quarantined_memory_review_only():
    assert any(d["decision_status"] == "REVIEW_ONLY_QUARANTINED" for d in build_p26_3_bridge(Path.cwd())["decisions"])


def test_p26_3_supports_reject_and_defer_decisions():
    statuses = {d["decision_status"] for d in build_p26_3_bridge(Path.cwd())["decisions"]}
    assert {"REJECTED", "DEFERRED"} <= statuses


def test_p26_3_approved_for_review_without_truth_claim():
    decision = [d for d in build_p26_3_bridge(Path.cwd())["decisions"] if d["decision_status"] == "APPROVED_FOR_REVIEW"][0]
    assert decision["approved_for_review_without_truth_claim"] is True
    assert decision["truth_claimed"] is False


def test_p26_3_no_tool_authorization_live_effects_deletion_or_orp_bypass():
    layer = build_p26_3_bridge(Path.cwd())
    assert all(not r.get("tools_authorized") for r in layer["receipt_chain"])
    assert all(not r.get("live_external_side_effects_created") for r in layer["receipt_chain"])
    assert all(not r.get("deletion_performed") for r in layer["receipt_chain"])
    assert all(not r.get("orp_bypassed") for r in layer["receipt_chain"])


def test_p26_3_phase19_and_phase24_preserved():
    manifest = build_p26_3_bridge(Path.cwd())["manifest"]
    assert manifest["phase19_yellow_preserved"] is True
    assert manifest["phase24_infrastructure_only_preserved"] is True


def test_p26_3_gate_accepts_green_summary():
    assert validate_p26_3_gate(_summary())["ok"] is True


def test_p26_3_gate_rejects_truth_authority_and_orp_bypass():
    assert validate_p26_3_gate(_summary(memory_treated_as_truth=True))["ok"] is False
    assert validate_p26_3_gate(_summary(recall_treated_as_authority=True))["ok"] is False
    assert validate_p26_3_gate(_summary(orp_bypassed=True))["ok"] is False
