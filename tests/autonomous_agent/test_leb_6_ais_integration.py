"""LEB-6 AIS integration over local evidence receipts tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.ais_integration import (
    build_ais_integration,
    build_evidence_patch_hygiene_tasks,
    replay_ais_integration,
    validate_leb6_gate,
)
from hg_runtime.local_evidence_bridge.evidence_fever_hooks import build_evidence_fever_report
from hg_runtime.local_evidence_bridge.evidence_health_scan import build_evidence_health_findings
from hg_runtime.local_evidence_bridge.evidence_quarantine_hooks import build_evidence_quarantine_candidates
from hg_runtime.local_evidence_bridge.evidence_security_hooks import build_evidence_security_findings
from hg_runtime.local_evidence_bridge.redaction import secret_scan
from hg_runtime.local_evidence_bridge.schemas import PHASE19_VERDICT, PHASE24_STATUS

ROOT = Path(__file__).resolve().parents[2]


def _layer():
    return build_ais_integration(ROOT)


def _gate_summary(**overrides):
    data = {
        "verdict": "GREEN_LEB_6_AIS_INTEGRATION",
        "health_findings_written": True,
        "quarantine_candidates_written": True,
        "fever_report_written": True,
        "security_findings_written": True,
        "patch_hygiene_tasks_written": True,
        "ais_integration_manifest_written": True,
        "ais_finding_not_authority": True,
        "quarantine_candidate_not_deletion": True,
        "fever_restricts_never_unlocks": True,
        "security_finding_defensive_only": True,
        "patch_hygiene_task_not_patch": True,
        "local_evidence_non_authoritative": True,
        "no_automatic_patching": True,
        "no_deletion": True,
        "no_auto_quarantine_enforcement": True,
        "replay_preserves_integration_hashes": True,
        "secret_redaction_passed": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


# --- Construction ----------------------------------------------------------

def test_leb6_builds_all_finding_kinds():
    m = _layer()["manifest"]
    assert m["health_finding_count"] > 0
    assert m["quarantine_candidate_count"] > 0
    assert m["security_finding_count"] > 0
    assert m["patch_hygiene_task_count"] > 0


def test_leb6_ais_finding_is_not_authority():
    for f in _layer()["health"]:
        assert f["finding_is_authority"] is False


def test_leb6_quarantine_candidate_is_not_deletion():
    for q in _layer()["quarantine"]:
        assert q["quarantine_candidate_is_deletion"] is False
        assert q["original_preserved"] is True
        assert q["deletion_performed"] is False


def test_leb6_fever_restricts_never_unlocks():
    fever = _layer()["fever"]
    assert fever["fever_unlocks_action"] is False
    assert fever["unlock_actions"] == []


def test_leb6_high_fever_has_restrictions():
    fever = _layer()["fever"]
    if fever["fever_restricts"]:
        assert fever["restrictions"]


def test_leb6_security_finding_is_defensive_only():
    for s in _layer()["security"]:
        assert s["defensive_only"] is True
        assert s["offensive_capability"] is False
        assert s["exploit_generated"] is False
        assert s["audit_mode"] == "DEFENSIVE_ONLY_STATIC_LOCAL"


def test_leb6_patch_hygiene_task_is_not_patch():
    for t in _layer()["patch_tasks"]:
        assert t["patch_hygiene_task_is_patch"] is False
        assert t["automatic_patching"] is False
        assert t["operator_approval_required"] is True


def test_leb6_local_evidence_remains_non_authoritative():
    assert _layer()["manifest"]["local_evidence_is_authoritative"] is False


def test_leb6_no_auto_quarantine_enforcement():
    assert _layer()["manifest"]["auto_quarantine_enforced"] is False


def test_leb6_no_automatic_patching_or_deletion():
    m = _layer()["manifest"]
    assert m["automatic_patching_enabled"] is False
    assert m["deletion_performed"] is False


# --- Hook units ------------------------------------------------------------

def test_leb6_redaction_flagged_raises_yellow_health():
    findings = build_evidence_health_findings([
        {"receipt_id": "r1", "receipt_hash": "h1", "secret_like_content_redacted": True},
    ])
    assert findings[0]["severity"] == "YELLOW"
    assert findings[0]["signal_type"] == "evidence_redaction_flagged"


def test_leb6_clean_receipt_only_quarantine_when_suspicious():
    clean = [{"receipt_id": "r1", "receipt_hash": "h1", "secret_like_content_redacted": False}]
    assert build_evidence_quarantine_candidates(clean) == []


def test_leb6_fever_from_clean_findings_is_normal():
    findings = build_evidence_health_findings([{"receipt_id": "r1", "receipt_hash": "h1"}])
    fever = build_evidence_fever_report(findings)
    assert fever["fever_unlocks_action"] is False


def test_leb6_security_baseline_finding_present():
    findings = build_evidence_security_findings([{"receipt_id": "r1", "receipt_hash": "h1"}])
    assert any(f["finding_type"] == "evidence_path_and_redaction_checked" for f in findings)


def test_leb6_patch_tasks_derive_from_security_findings():
    sec = build_evidence_security_findings([{"receipt_id": "r1", "receipt_hash": "h1"}])
    tasks = build_evidence_patch_hygiene_tasks(sec)
    assert len(tasks) == len(sec)


# --- Replay & secrets ------------------------------------------------------

def test_leb6_replay_preserves_integration_hashes():
    assert _layer()["replay"]["replay_preserves_integration_hashes"] is True


def test_leb6_replay_rejects_mutated_finding():
    layer = _layer()
    health = [dict(f) for f in layer["health"]]
    health[0]["severity"] = "RED"
    replay = replay_ais_integration(
        health, layer["quarantine"], layer["security"], layer["patch_tasks"], layer["fever"], layer["manifest"]
    )
    assert replay["replay_preserves_integration_hashes"] is False


def test_leb6_no_secret_material_in_artifacts():
    assert secret_scan(_layer()) is True


# --- Prior phases ----------------------------------------------------------

def test_leb6_preserves_phase19_yellow():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")


def test_leb6_preserves_phase24_infrastructure_only():
    assert PHASE24_STATUS == "infrastructure_only"


# --- Gate ------------------------------------------------------------------

def test_leb6_gate_passes_on_full_summary():
    assert validate_leb6_gate(_gate_summary())["ok"] is True


def test_leb6_gate_refuses_if_finding_is_authority():
    assert validate_leb6_gate(_gate_summary(ais_finding_treated_as_authority=True))["ok"] is False


def test_leb6_gate_refuses_if_quarantine_is_deletion():
    assert validate_leb6_gate(_gate_summary(quarantine_candidate_not_deletion=False))["ok"] is False


def test_leb6_gate_refuses_if_fever_unlocks():
    assert validate_leb6_gate(_gate_summary(fever_unlocks_action=True))["ok"] is False


def test_leb6_gate_refuses_if_automatic_patching():
    assert validate_leb6_gate(_gate_summary(automatic_patching_enabled=True))["ok"] is False


def test_leb6_gate_refuses_if_deletion():
    assert validate_leb6_gate(_gate_summary(deletion_performed=True))["ok"] is False


def test_leb6_gate_refuses_if_evidence_treated_as_truth():
    assert validate_leb6_gate(_gate_summary(evidence_treated_as_truth=True))["ok"] is False


def test_leb6_gate_refuses_if_offensive_capability():
    assert validate_leb6_gate(_gate_summary(offensive_capability=True))["ok"] is False
