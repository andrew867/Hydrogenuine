"""AIS-1 record health scanner tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_runtime.agent_immune_system.artifact_writer import build_record_health_layer
from hg_runtime.agent_immune_system.record_health import scan_bundle
from hg_runtime.agent_immune_system.record_health_fixtures import (
    detection_fixture_dirs,
    materialize_record_health_fixtures,
)
from hg_runtime.agent_immune_system.record_health_gate import VERDICT_GREEN, validate_ais1_gate
from hg_runtime.agent_immune_system.redaction import secret_scan
from hg_runtime.agent_immune_system.schemas import PHASE19_VERDICT, PHASE24_STATUS

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = ROOT / "fixtures" / "ais" / "record_health"


def _gate_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "ais0_green": True,
        "record_health_findings_written": True,
        "finding_count": 5,
        "health_signals_written": True,
        "scan_manifest_written": True,
        "detects_missing_receipt": True,
        "detects_missing_gate_result": True,
        "detects_missing_report_snapshot": True,
        "detects_missing_redaction_audit": True,
        "detects_broken_hash_chain": True,
        "detects_replay_mismatch": True,
        "detects_report_proof_mismatch": True,
        "detects_boundary_assertion_violations": True,
        "detects_stale_yellow_review": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "missing_receipt_blocks_green": True,
        "detection_is_not_authority": True,
        "no_automatic_patching": True,
        "no_deletion_performed": True,
        "replay_preserves_scan_hashes": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


@pytest.fixture(scope="module", autouse=True)
def _ensure_fixtures():
    materialize_record_health_fixtures()


def test_ais1_materializes_fixture_root():
    assert FIXTURE_ROOT.exists()


def test_ais1_detects_missing_receipt():
    findings = scan_bundle(FIXTURE_ROOT / "missing_receipt")
    assert any(f["finding_type"] == "missing_receipt" for f in findings)
    assert any(f.get("blocks_green") for f in findings)


def test_ais1_detects_missing_gate_result():
    findings = scan_bundle(FIXTURE_ROOT / "missing_gate_result")
    assert any(f["finding_type"] == "missing_gate_result" for f in findings)


def test_ais1_detects_missing_report_snapshot():
    findings = scan_bundle(FIXTURE_ROOT / "missing_report_snapshot")
    assert any(f["finding_type"] == "missing_report_snapshot" for f in findings)


def test_ais1_detects_missing_redaction_audit():
    findings = scan_bundle(FIXTURE_ROOT / "missing_redaction_audit")
    assert any(f["finding_type"] == "missing_redaction_audit" for f in findings)


def test_ais1_detects_broken_hash_chain():
    findings = scan_bundle(FIXTURE_ROOT / "broken_hash_chain")
    assert any(f["finding_type"] == "broken_hash_chain" for f in findings)


def test_ais1_detects_replay_mismatch():
    findings = scan_bundle(FIXTURE_ROOT / "replay_mismatch")
    assert any(f["finding_type"] == "replay_mismatch" for f in findings)


def test_ais1_detects_report_proof_mismatch():
    findings = scan_bundle(FIXTURE_ROOT / "report_proof_mismatch")
    assert any(f["finding_type"] == "report_proof_mismatch" for f in findings)


def test_ais1_detects_stale_yellow_review():
    findings = scan_bundle(FIXTURE_ROOT / "stale_yellow_review")
    assert any(f["finding_type"] == "stale_yellow_requires_review" for f in findings)


def test_ais1_detects_dirty_report_churn():
    findings = scan_bundle(FIXTURE_ROOT / "dirty_report_churn")
    assert any(f["finding_type"] == "dirty_report_churn" for f in findings)


def test_ais1_detects_untracked_generated_artifact():
    findings = scan_bundle(FIXTURE_ROOT / "untracked_artifact")
    assert any(f["finding_type"] == "untracked_generated_artifact" for f in findings)


def test_ais1_detects_phase19_launder_attempt():
    findings = scan_bundle(FIXTURE_ROOT / "phase19_launder_attempt")
    assert any(f["finding_type"] == "phase19_yellow_laundering" for f in findings)


def test_ais1_detects_phase24_launder_attempt():
    findings = scan_bundle(FIXTURE_ROOT / "phase24_launder_attempt")
    assert any(f["finding_type"] == "phase24_infrastructure_laundering" for f in findings)


def test_ais1_healthy_fixture_has_no_blocking_findings():
    findings = scan_bundle(FIXTURE_ROOT / "healthy_minimal")
    assert not any(f.get("blocks_green") for f in findings)


def test_ais1_build_layer_replay_preserves_hashes():
    out = build_record_health_layer(detection_fixture_dirs())
    assert out["replay"]["replay_preserves_scan_hashes"] is True


def test_ais1_no_authority_in_findings():
    out = build_record_health_layer(detection_fixture_dirs())
    assert all(not f.get("authority_granted") for f in out["findings"])


def test_ais1_secret_scan_passes():
    out = build_record_health_layer(detection_fixture_dirs())
    assert secret_scan(out) is True


def test_ais1_preserves_phase19_yellow():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")


def test_ais1_preserves_phase24_infrastructure_only():
    assert PHASE24_STATUS == "infrastructure_only"


def test_ais1_gate_passes_on_full_summary():
    assert validate_ais1_gate(_gate_summary())["ok"] is True


def test_ais1_gate_refuses_missing_receipt_blocks_green_false():
    assert validate_ais1_gate(_gate_summary(missing_receipt_blocks_green=False))["ok"] is False


def test_ais1_gate_refuses_authority_granted():
    assert validate_ais1_gate(_gate_summary(authority_granted=True))["ok"] is False


def test_ais1_gate_refuses_deletion_performed():
    assert validate_ais1_gate(_gate_summary(deletion_performed=True))["ok"] is False


def test_ais1_gate_refuses_phase19_marked_green():
    assert validate_ais1_gate(_gate_summary(phase19_marked_green=True))["ok"] is False
