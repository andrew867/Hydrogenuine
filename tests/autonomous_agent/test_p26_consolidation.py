"""P26 consolidation tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.experience_ledger.gate import validate_p26_consolidation_gate
from scripts.evals.autonomous_agent_p26_consolidation_gate import build_consolidation_layer


def _summary(**overrides):
    data = {
        "verdict": "GREEN_P26_PERSISTENT_MEMORY_EXPERIENCE_LEDGER_CONSOLIDATION",
        "p26_0_green": True,
        "p26_1_green": True,
        "p26_2_green": True,
        "p26_3_green": True,
        "p26_4_green": True,
        "exact_p26_gate_exists": True,
        "component_index_written": True,
        "boundary_matrix_written": True,
        "consolidation_summary_written": True,
        "memory_is_not_truth": True,
        "recall_is_not_authority": True,
        "experience_is_not_evidence_by_itself": True,
        "ledger_entry_is_not_belief": True,
        "promotion_request_is_not_promotion": True,
        "orp_gated_promotion_only": True,
        "retraction_quarantine_supported": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_p26_consolidation_loads_p26_0_through_4_proofs():
    layer = build_consolidation_layer()
    assert [entry["phase"] for entry in layer["component_index"]["components"]] == ["P26-0", "P26-1", "P26-2", "P26-3", "P26-4"]
    assert all(entry["green"] for entry in layer["component_index"]["components"])


def test_p26_consolidation_boundary_matrix_preserves_required_boundaries():
    boundary = build_consolidation_layer()["boundary_matrix"]
    assert boundary["memory_is_not_truth"] is True
    assert boundary["recall_is_not_authority"] is True
    assert boundary["experience_is_not_evidence_by_itself"] is True
    assert boundary["ledger_entry_is_not_belief"] is True
    assert boundary["promotion_request_is_not_promotion"] is True
    assert boundary["orp_gated_promotion_only"] is True
    assert boundary["automatic_belief_promotion"] is False
    assert boundary["tool_authorization"] is False
    assert boundary["deletion"] is False
    assert boundary["live_effects"] is False
    assert boundary["pdf_ocr"] is False
    assert boundary["html"] is False
    assert boundary["arbitrary_ingestion"] is False


def test_p26_consolidation_phase19_and_phase24_preserved():
    boundary = build_consolidation_layer()["boundary_matrix"]
    assert boundary["phase19_yellow_preserved"] is True
    assert boundary["phase24_infrastructure_only_preserved"] is True


def test_p26_consolidation_exact_gate_accepts_green():
    assert validate_p26_consolidation_gate(_summary())["ok"] is True


def test_p26_consolidation_rejects_if_p26_3_missing():
    assert validate_p26_consolidation_gate(_summary(p26_3_green=False))["ok"] is False


def test_p26_consolidation_rejects_if_p26_4_missing():
    assert validate_p26_consolidation_gate(_summary(p26_4_green=False))["ok"] is False


def test_p26_consolidation_rejects_if_memory_marked_truth():
    assert validate_p26_consolidation_gate(_summary(memory_treated_as_truth=True))["ok"] is False


def test_p26_consolidation_rejects_if_recall_grants_authority():
    assert validate_p26_consolidation_gate(_summary(recall_treated_as_authority=True))["ok"] is False


def test_p26_consolidation_rejects_if_promotion_request_auto_applied():
    assert validate_p26_consolidation_gate(_summary(promotion_request_auto_applied=True))["ok"] is False


def test_p26_consolidation_report_paths_are_declared():
    layer = build_consolidation_layer()
    assert all(entry["report"].startswith("docs/reports/phases/") for entry in layer["component_index"]["components"])
