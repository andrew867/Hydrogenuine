"""Phase 25 advisory self-improvement loop tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_runtime.advisory_self_improvement.fixtures import build_phase25_layer, replay_phase25
from hg_runtime.advisory_self_improvement.gate import validate_phase25_gate
from hg_runtime.advisory_self_improvement.proposal_generator import (
    build_improvement_proposal,
    build_refusal_record,
)
from hg_runtime.advisory_self_improvement.redaction import secret_scan
from hg_runtime.advisory_self_improvement.risk_classifier import risk_for_category
from hg_runtime.advisory_self_improvement.schemas import (
    PHASE19_VERDICT,
    PHASE24_STATUS,
    REFUSAL_REASONS,
    Phase25BoundaryError,
)

ROOT = Path(__file__).resolve().parents[2]


def _layer():
    return build_phase25_layer(ROOT)


def _summary(**overrides):
    data = {
        "verdict": "GREEN_PHASE25_ADVISORY_SELF_IMPROVEMENT",
        "sle_rc_consolidation_green": True,
        "inputs_read": True,
        "proposals_written": True,
        "risk_records_written": True,
        "operator_review_tasks_written": True,
        "refusal_records_written": True,
        "all_refusal_reasons_present": True,
        "all_proposals_require_review": True,
        "all_review_tasks_pending": True,
        "proposal_not_patch_permission": True,
        "advisory_not_authority": True,
        "review_task_not_implementation": True,
        "no_self_merge": True,
        "no_patch_application": True,
        "no_tool_authorization": True,
        "no_authority_change": True,
        "no_self_marked_better": True,
        "phase19_not_marked_green": True,
        "phase24_not_marked_full_green": True,
        "no_belief_promotion": True,
        "no_provider_or_web_enabled": True,
        "no_pdf_ocr_enabled": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_manifest_hash": True,
        "replay_preserves_proposal_hashes": True,
        "replay_preserves_refusal_hashes": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


# --- Generation ------------------------------------------------------------

def test_phase25_emits_proposals_risks_tasks_refusals():
    layer = _layer()
    assert layer["proposals"]
    assert layer["risks"]
    assert layer["review_tasks"]
    assert layer["refusals"]


def test_phase25_proposals_are_advisory_only():
    for p in _layer()["proposals"]:
        assert p["proposal_is_patch_permission"] is False
        assert p["proposal_is_self_authorization"] is False
        assert p["requires_operator_review"] is True
        assert p["status"] == "ADVISORY_PROPOSED"


def test_phase25_all_required_refusal_cases_present():
    reasons = {r["refusal_reason"] for r in _layer()["refusals"]}
    assert REFUSAL_REASONS <= reasons


def test_phase25_refusals_did_not_perform_action():
    for r in _layer()["refusals"]:
        assert r["action_performed"] is False
        assert r["status"] == "REFUSED"


def test_phase25_review_tasks_pending_not_implementation():
    for t in _layer()["review_tasks"]:
        assert t["status"] == "PENDING_OPERATOR_REVIEW"
        assert t["review_task_is_implementation"] is False
        assert t["review_task_is_approval"] is False


def test_phase25_proposal_builder_rejects_unknown_category():
    with pytest.raises(Phase25BoundaryError):
        build_improvement_proposal(proposal_id="x", category="NOPE", title="t", rationale="r", depends_on_inputs=[])


def test_phase25_refusal_builder_rejects_unknown_reason():
    with pytest.raises(Phase25BoundaryError):
        build_refusal_record(refusal_id="x", requested_action="a", refusal_reason="NOPE")


def test_phase25_risk_for_gap_reconciliation_requires_review():
    assert risk_for_category("GAP_RECONCILIATION") == "REQUIRES_OPERATOR_REVIEW"
    assert risk_for_category("DOCUMENTATION") == "LOW"


# --- Manifest / replay -----------------------------------------------------

def test_phase25_manifest_flags_full_refusal_coverage():
    assert _layer()["manifest"]["all_refusal_reasons_present"] is True


def test_phase25_replay_preserves_hashes():
    layer = _layer()
    replay = replay_phase25(
        ROOT,
        layer["manifest"]["manifest_hash"],
        [p["record_hash"] for p in layer["proposals"]],
        [r["record_hash"] for r in layer["refusals"]],
    )
    assert replay["replay_preserves_manifest_hash"] is True
    assert replay["replay_preserves_proposal_hashes"] is True
    assert replay["replay_preserves_refusal_hashes"] is True


def test_phase25_replay_rejects_mutation():
    replay = replay_phase25(ROOT, "mutated", ["mutated"], ["mutated"])
    assert replay["replay_preserves_manifest_hash"] is False


def test_phase25_secret_scan_passes():
    assert secret_scan(_layer()) is True


def test_phase25_preserves_phase19_and_phase24():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")
    assert PHASE24_STATUS == "infrastructure_only"


# --- Gate ------------------------------------------------------------------

def test_phase25_gate_passes_full_summary():
    assert validate_phase25_gate(_summary())["ok"] is True


def test_phase25_gate_refuses_patch_applied():
    assert validate_phase25_gate(_summary(patch_applied=True))["ok"] is False
    assert validate_phase25_gate(_summary(patch_request_applied=True))["ok"] is False


def test_phase25_gate_refuses_self_authorization():
    assert validate_phase25_gate(_summary(proposal_is_self_authorization=True))["ok"] is False
    assert validate_phase25_gate(_summary(self_merge_performed=True))["ok"] is False


def test_phase25_gate_refuses_authority_or_tools():
    assert validate_phase25_gate(_summary(authority_granted=True))["ok"] is False
    assert validate_phase25_gate(_summary(tools_authorized=True))["ok"] is False


def test_phase25_gate_refuses_phase19_or_phase24_laundering():
    assert validate_phase25_gate(_summary(phase19_marked_green=True))["ok"] is False
    assert validate_phase25_gate(_summary(phase24_marked_full_green=True))["ok"] is False


def test_phase25_gate_refuses_provider_web_pdf():
    assert validate_phase25_gate(_summary(provider_enabled=True))["ok"] is False
    assert validate_phase25_gate(_summary(web_enabled=True))["ok"] is False
    assert validate_phase25_gate(_summary(pdf_ocr_enabled=True))["ok"] is False


def test_phase25_gate_refuses_belief_promotion():
    assert validate_phase25_gate(_summary(belief_promotion_automatic=True))["ok"] is False


def test_phase25_gate_refuses_missing_refusal_coverage():
    assert validate_phase25_gate(_summary(all_refusal_reasons_present=False))["ok"] is False
