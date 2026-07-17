"""Reviewed Local Evidence Beta consolidation tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATE_PATH = ROOT / "scripts/evals/autonomous_agent_reviewed_local_evidence_beta_gate.py"


def _gate_module():
    spec = importlib.util.spec_from_file_location("reviewed_local_evidence_beta_gate", GATE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _summary():
    return _gate_module().build_reviewed_beta_summary()


def test_reviewed_beta_includes_safe_local_evidence_alpha():
    summary = _summary()
    assert summary["safe_local_evidence_alpha_green"] is True


def test_reviewed_beta_includes_orp0_through_orp4():
    summary = _summary()
    assert summary["orp0_through_orp4_green"] is True
    assert len(summary["phase_index"]) == 6


def test_reviewed_beta_phase_reports_present():
    assert _summary()["all_phase_reports_present"] is True


def test_reviewed_beta_no_live_web_or_providers():
    summary = _summary()
    assert summary["web_browse_performed"] is False
    assert summary["external_provider_calls_made"] is False


def test_reviewed_beta_no_arbitrary_file_ingestion_or_pdf_ocr():
    summary = _summary()
    assert summary["arbitrary_file_ingestion_enabled"] is False
    assert summary["pdf_ingestion_enabled"] is False


def test_reviewed_beta_no_truth_or_automatic_promotion():
    summary = _summary()
    assert summary["evidence_treated_as_truth"] is False
    assert summary["operator_review_treated_as_truth"] is False
    assert summary["belief_promotion_automatic"] is False


def test_reviewed_beta_no_authority_patch_or_deletion():
    summary = _summary()
    assert summary["authority_granted"] is False
    assert summary["tools_authorized"] is False
    assert summary["patch_request_applied"] is False
    assert summary["deletion_performed"] is False


def test_reviewed_beta_preserves_phase19_and_phase24():
    summary = _summary()
    assert summary["phase19_yellow_preserved"] is True
    assert summary["phase24_infrastructure_only_preserved"] is True


def test_reviewed_beta_validation_passes():
    module = _gate_module()
    summary = module.build_reviewed_beta_summary()
    assert module.validate_reviewed_beta(summary)["ok"] is True


def test_reviewed_beta_validation_rejects_truth_claim():
    module = _gate_module()
    summary = module.build_reviewed_beta_summary()
    summary["evidence_treated_as_truth"] = True
    assert module.validate_reviewed_beta(summary)["ok"] is False


def test_reviewed_beta_validation_rejects_missing_orp():
    module = _gate_module()
    summary = module.build_reviewed_beta_summary()
    summary["orp0_through_orp4_green"] = False
    assert module.validate_reviewed_beta(summary)["ok"] is False
