"""MREC-002 proof bundle forgery negative tests.

Tests proof bundle consumption paths for forgery, tamper, replay,
and laundering vectors. Each test targets a verified code path in:
  - hg_runtime.agent_immune_system (record health scanners)
  - hg_runtime.safe_local_evidence_rc (proof bundle indexer, gate reader)

Proof bundle existence is not truth. Proof bundle existence is not authority.
Test pass is not deployment permission. Model output is not truth.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hg_runtime.agent_immune_system.record_health import scan_bundle
from hg_runtime.agent_immune_system.record_health_gate import validate_ais1_gate
from hg_runtime.agent_immune_system.schemas import PHASE19_VERDICT, PHASE24_STATUS


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


def _minimal_gate(verdict: str = "GREEN_FIXTURE", **overrides) -> dict:
    data = {
        "ok": True,
        "verdict": verdict,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
    }
    data.update(overrides)
    return data


def _minimal_bundle(tmp_path: Path, *, gate: dict | None = None, report_verdict: str | None = None,
                     receipt_chain: list[dict] | None = None, replay: dict | None = None,
                     redaction: dict | None = None, boundary: dict | None = None) -> Path:
    bundle = tmp_path / "test_bundle"
    if gate is not None:
        _write_json(bundle / "gate_result.json", gate)
    if report_verdict is not None:
        _write_text(bundle / "report_snapshot.md", f"## Verdict\n\n`{report_verdict}`\n")
    if receipt_chain is not None:
        _write_jsonl(bundle / "receipt_chain.jsonl", receipt_chain)
    if replay is not None:
        _write_json(bundle / "replay_result.json", replay)
    if redaction is not None:
        _write_json(bundle / "redaction_audit.json", redaction)
    if boundary is not None:
        _write_json(bundle / "boundary_assertions.json", boundary)
    return bundle


# ---------------------------------------------------------------------------
# TP-FORGERY-001: report_verdict_mismatch_expected bypass
# ---------------------------------------------------------------------------

class TestReportVerdictMismatchBypass:

    def test_mismatch_detected_without_bypass(self, tmp_path):
        bundle = _minimal_bundle(
            tmp_path,
            gate=_minimal_gate("GREEN_FIXTURE"),
            report_verdict="RED_FIXTURE_DIFFERENT",
            receipt_chain=[{"receipt_id": "r1", "record_hash": "h1"}],
            replay={"ok": True, "replay_hash_is_stable": True},
            redaction={"secret_redaction_passed": True},
        )
        findings = scan_bundle(bundle)
        assert any(f["finding_type"] == "report_proof_mismatch" for f in findings)

    def test_mismatch_suppressed_by_bypass_flag(self, tmp_path):
        """Documents that report_verdict_mismatch_expected silences detection."""
        bundle = _minimal_bundle(
            tmp_path,
            gate=_minimal_gate("GREEN_FIXTURE", report_verdict_mismatch_expected=True),
            report_verdict="RED_FIXTURE_DIFFERENT",
            receipt_chain=[{"receipt_id": "r1", "record_hash": "h1"}],
            replay={"ok": True, "replay_hash_is_stable": True},
            redaction={"secret_redaction_passed": True},
        )
        findings = scan_bundle(bundle)
        assert not any(f["finding_type"] == "report_proof_mismatch" for f in findings)


# ---------------------------------------------------------------------------
# TP-FORGERY-002/003: Phase laundering via report text
# ---------------------------------------------------------------------------

class TestPhaseLaunderingViaReportText:

    def test_phase24_text_laundering_detected(self, tmp_path):
        bundle = _minimal_bundle(
            tmp_path,
            gate=_minimal_gate(),
            report_verdict="GREEN_FIXTURE",
            receipt_chain=[{"receipt_id": "r1", "record_hash": "h1"}],
            replay={"ok": True, "replay_hash_is_stable": True},
            redaction={"secret_redaction_passed": True},
        )
        report = bundle / "report_snapshot.md"
        report.write_text(
            "## Verdict\n\n`GREEN_FIXTURE`\n\nPhase 24 full overnight GREEN achieved.\n",
            encoding="utf-8",
        )
        findings = scan_bundle(bundle)
        assert any(f["finding_type"] == "phase24_infrastructure_laundering" for f in findings)

    def test_phase19_gate_flag_laundering_detected(self, tmp_path):
        bundle = _minimal_bundle(
            tmp_path,
            gate=_minimal_gate(phase19_marked_green=True, phase19_verdict="GREEN_PHASE19"),
            report_verdict="GREEN_FIXTURE",
            receipt_chain=[{"receipt_id": "r1", "record_hash": "h1"}],
            replay={"ok": True, "replay_hash_is_stable": True},
            redaction={"secret_redaction_passed": True},
        )
        findings = scan_bundle(bundle)
        assert any(f["finding_type"] == "phase19_yellow_laundering" for f in findings)
        assert any(f.get("severity") == "PANIC" for f in findings if f["finding_type"] == "phase19_yellow_laundering")


# ---------------------------------------------------------------------------
# TP-FORGERY-004: Replay with no hash passes silently
# ---------------------------------------------------------------------------

class TestReplayNoHash:

    def test_replay_no_hash_no_finding(self, tmp_path):
        """Documents gap: replay_result with ok=true but no hash is not flagged."""
        bundle = _minimal_bundle(
            tmp_path,
            gate=_minimal_gate(),
            report_verdict="GREEN_FIXTURE",
            receipt_chain=[{"receipt_id": "r1", "record_hash": "h1"}],
            replay={"ok": True},
            redaction={"secret_redaction_passed": True},
        )
        findings = scan_bundle(bundle)
        replay_findings = [f for f in findings if f["finding_type"] == "replay_mismatch"]
        assert len(replay_findings) == 0


# ---------------------------------------------------------------------------
# TP-FORGERY-005: Empty receipt chain with ok=true
# ---------------------------------------------------------------------------

class TestEmptyReceiptChain:

    def test_ok_true_empty_chain_detected(self, tmp_path):
        bundle = _minimal_bundle(
            tmp_path,
            gate=_minimal_gate(),
            report_verdict="GREEN_FIXTURE",
            receipt_chain=[],
            replay={"ok": True, "replay_hash_is_stable": True},
            redaction={"secret_redaction_passed": True},
        )
        findings = scan_bundle(bundle)
        assert any(f["finding_type"] == "missing_receipt" for f in findings)
        assert any(f.get("blocks_green") for f in findings)

    def test_ok_true_empty_chain_with_expected_ids(self, tmp_path):
        bundle = _minimal_bundle(
            tmp_path,
            gate=_minimal_gate(expected_receipt_ids=["r1", "r2"]),
            report_verdict="GREEN_FIXTURE",
            receipt_chain=[],
            replay={"ok": True, "replay_hash_is_stable": True},
            redaction={"secret_redaction_passed": True},
        )
        findings = scan_bundle(bundle)
        missing = [f for f in findings if f["finding_type"] == "missing_receipt"]
        assert len(missing) >= 2


# ---------------------------------------------------------------------------
# TP-FORGERY-006/007: Phase preservation flags false
# ---------------------------------------------------------------------------

class TestPhasePreservationFlags:

    def test_phase19_yellow_not_preserved_detected(self, tmp_path):
        bundle = _minimal_bundle(
            tmp_path,
            gate=_minimal_gate(phase19_yellow_preserved=False),
            report_verdict="GREEN_FIXTURE",
            receipt_chain=[{"receipt_id": "r1", "record_hash": "h1"}],
            replay={"ok": True, "replay_hash_is_stable": True},
            redaction={"secret_redaction_passed": True},
        )
        findings = scan_bundle(bundle)
        assert any(f["finding_type"] == "phase19_yellow_not_preserved" for f in findings)
        assert any(f.get("blocks_green") for f in findings)

    def test_phase24_not_preserved_detected(self, tmp_path):
        bundle = _minimal_bundle(
            tmp_path,
            gate=_minimal_gate(phase24_infrastructure_only_preserved=False),
            report_verdict="GREEN_FIXTURE",
            receipt_chain=[{"receipt_id": "r1", "record_hash": "h1"}],
            replay={"ok": True, "replay_hash_is_stable": True},
            redaction={"secret_redaction_passed": True},
        )
        findings = scan_bundle(bundle)
        assert any(f["finding_type"] == "phase24_infrastructure_not_preserved" for f in findings)
        assert any(f.get("blocks_green") for f in findings)


# ---------------------------------------------------------------------------
# TP-FORGERY-008: Boundary assertions not consumed
# ---------------------------------------------------------------------------

class TestBoundaryAssertionsNowConsumed:

    def test_forged_boundary_assertions_detected_by_scanner(self, tmp_path):
        """Gap closed: forged boundary_assertions.json now produces findings."""
        bundle = _minimal_bundle(
            tmp_path,
            gate=_minimal_gate(),
            report_verdict="GREEN_FIXTURE",
            receipt_chain=[{"receipt_id": "r1", "record_hash": "h1"}],
            replay={"ok": True, "replay_hash_is_stable": True},
            redaction={"secret_redaction_passed": True},
            boundary={
                "phase19_yellow_preserved": False,
                "no_live_effects": False,
                "no_tool_authorization": False,
                "forged_field": "this_should_be_caught",
            },
        )
        findings = scan_bundle(bundle)
        boundary_findings = [f for f in findings if "boundary" in f.get("finding_type", "")]
        assert len(boundary_findings) > 0
        assert any(f.get("assertion_key") == "phase19_yellow_preserved" for f in boundary_findings)


# ---------------------------------------------------------------------------
# TP-FORGERY-009: Redaction audit content not verified
# ---------------------------------------------------------------------------

class TestRedactionAuditContentNotVerified:

    def test_redaction_audit_secrets_found_true_not_caught(self, tmp_path):
        """Documents gap: redaction_audit content is not checked, only existence."""
        bundle = _minimal_bundle(
            tmp_path,
            gate=_minimal_gate(),
            report_verdict="GREEN_FIXTURE",
            receipt_chain=[{"receipt_id": "r1", "record_hash": "h1"}],
            replay={"ok": True, "replay_hash_is_stable": True},
            redaction={"secrets_found": True, "api_keys_found": True, "status": "DIRTY"},
        )
        findings = scan_bundle(bundle)
        redaction_findings = [f for f in findings if "redaction" in f.get("finding_type", "")]
        assert len(redaction_findings) == 0

    def test_missing_redaction_audit_still_detected(self, tmp_path):
        bundle = _minimal_bundle(
            tmp_path,
            gate=_minimal_gate(),
            report_verdict="GREEN_FIXTURE",
            receipt_chain=[{"receipt_id": "r1", "record_hash": "h1"}],
            replay={"ok": True, "replay_hash_is_stable": True},
        )
        findings = scan_bundle(bundle)
        assert any(f["finding_type"] == "missing_redaction_audit" for f in findings)


# ---------------------------------------------------------------------------
# TP-FORGERY-010: AIS-1 gate laundering refusals
# ---------------------------------------------------------------------------

class TestAIS1GateLaunderingRefusals:

    def _gate_summary(self, **overrides):
        data = {
            "verdict": "GREEN_AIS_1_RECORD_HEALTH_SCANNER",
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

    def test_boundary_assertion_detection_missing_rejected(self):
        result = validate_ais1_gate(self._gate_summary(detects_boundary_assertion_violations=False))
        assert result["ok"] is False

    def test_phase19_marked_green_rejected(self):
        result = validate_ais1_gate(self._gate_summary(phase19_marked_green=True))
        assert result["ok"] is False
        assert "phase19_marked_green" in result["failures"]

    def test_phase24_full_overnight_green_rejected(self):
        result = validate_ais1_gate(self._gate_summary(phase24_full_overnight_green=True))
        assert result["ok"] is False
        assert "phase24_full_overnight_green" in result["failures"]

    def test_tools_authorized_rejected(self):
        result = validate_ais1_gate(self._gate_summary(tools_authorized=True))
        assert result["ok"] is False

    def test_web_browse_rejected(self):
        result = validate_ais1_gate(self._gate_summary(web_browse_performed=True))
        assert result["ok"] is False

    def test_external_provider_rejected(self):
        result = validate_ais1_gate(self._gate_summary(external_provider_calls_made=True))
        assert result["ok"] is False

    def test_live_effects_rejected(self):
        result = validate_ais1_gate(self._gate_summary(live_external_side_effects_created=True))
        assert result["ok"] is False

    def test_repair_recommendation_as_permission_rejected(self):
        result = validate_ais1_gate(self._gate_summary(repair_recommendation_is_patch_permission=True))
        assert result["ok"] is False

    def test_missing_detects_replay_mismatch_rejected(self):
        result = validate_ais1_gate(self._gate_summary(detects_replay_mismatch=False))
        assert result["ok"] is False

    def test_missing_detects_report_proof_mismatch_rejected(self):
        result = validate_ais1_gate(self._gate_summary(detects_report_proof_mismatch=False))
        assert result["ok"] is False

    def test_missing_proof_bundle_valid_rejected(self):
        result = validate_ais1_gate(self._gate_summary(proof_bundle_valid=False))
        assert result["ok"] is False

    def test_zero_findings_rejected(self):
        result = validate_ais1_gate(self._gate_summary(finding_count=0))
        assert result["ok"] is False

    def test_valid_gate_passes(self):
        result = validate_ais1_gate(self._gate_summary())
        assert result["ok"] is True


# ---------------------------------------------------------------------------
# TP-FORGERY-011: Proof bundle indexer wrong verdict
# ---------------------------------------------------------------------------

class TestProofBundleIndexerWrongVerdict:

    def test_wrong_verdict_not_green(self, tmp_path):
        from hg_runtime.safe_local_evidence_rc.gate_status_reader import latest_gate_result

        proof_root = tmp_path / "docs/proofs/autonomous_agent_zero/TEST-ROOT"
        ts_dir = proof_root / "20260623T000000Z"
        ts_dir.mkdir(parents=True)
        _write_json(ts_dir / "gate_result.json", {"verdict": "RED_WRONG_VERDICT"})

        verdict, bundle_path, data = latest_gate_result(tmp_path, "TEST-ROOT")
        assert verdict == "RED_WRONG_VERDICT"
        assert data["verdict"] == "RED_WRONG_VERDICT"

    def test_missing_proof_root_returns_unknown(self, tmp_path):
        from hg_runtime.safe_local_evidence_rc.gate_status_reader import latest_gate_result

        (tmp_path / "docs/proofs/autonomous_agent_zero/MISSING-ROOT").mkdir(parents=True)
        verdict, bundle_path, data = latest_gate_result(tmp_path, "MISSING-ROOT")
        assert verdict == "UNKNOWN"
        assert data is None

    def test_gate_status_reader_picks_latest_sorted(self, tmp_path):
        from hg_runtime.safe_local_evidence_rc.gate_status_reader import latest_gate_result

        proof_root = tmp_path / "docs/proofs/autonomous_agent_zero/MULTI-ROOT"
        early = proof_root / "20260101T000000Z"
        late = proof_root / "20260623T000000Z"
        early.mkdir(parents=True)
        late.mkdir(parents=True)
        _write_json(early / "gate_result.json", {"verdict": "GREEN_EARLY"})
        _write_json(late / "gate_result.json", {"verdict": "RED_LATE"})

        verdict, _, _ = latest_gate_result(tmp_path, "MULTI-ROOT")
        assert verdict == "RED_LATE"


# ---------------------------------------------------------------------------
# TP-FORGERY-012: Replay result ok=false
# ---------------------------------------------------------------------------

class TestReplayResultFailed:

    def test_replay_ok_false_detected(self, tmp_path):
        bundle = _minimal_bundle(
            tmp_path,
            gate=_minimal_gate(),
            report_verdict="GREEN_FIXTURE",
            receipt_chain=[{"receipt_id": "r1", "record_hash": "h1"}],
            replay={"ok": False},
            redaction={"secret_redaction_passed": True},
        )
        findings = scan_bundle(bundle)
        assert any(f["finding_type"] == "replay_mismatch" for f in findings)
        assert any(f.get("blocks_green") for f in findings)

    def test_replay_forced_mismatch_detected(self, tmp_path):
        bundle = _minimal_bundle(
            tmp_path,
            gate=_minimal_gate(),
            report_verdict="GREEN_FIXTURE",
            receipt_chain=[{"receipt_id": "r1", "record_hash": "h1"}],
            replay={"ok": True, "forced_mismatch": True},
            redaction={"secret_redaction_passed": True},
        )
        findings = scan_bundle(bundle)
        assert any(f["finding_type"] == "replay_mismatch" for f in findings)


# ---------------------------------------------------------------------------
# Additional: Broken hash chain with specific link
# ---------------------------------------------------------------------------

class TestBrokenHashChainSpecific:

    def test_broken_link_at_index_2(self, tmp_path):
        bundle = _minimal_bundle(
            tmp_path,
            gate=_minimal_gate(expected_receipt_ids=["r1", "r2", "r3"]),
            report_verdict="GREEN_FIXTURE",
            receipt_chain=[
                {"receipt_id": "r1", "record_hash": "h1", "prev_hash": None},
                {"receipt_id": "r2", "record_hash": "h2", "prev_hash": "h1"},
                {"receipt_id": "r3", "record_hash": "h3", "prev_hash": "WRONG"},
            ],
            replay={"ok": True, "replay_hash_is_stable": True},
            redaction={"secret_redaction_passed": True},
        )
        findings = scan_bundle(bundle)
        chain_findings = [f for f in findings if f["finding_type"] == "broken_hash_chain"]
        assert len(chain_findings) == 1
        assert chain_findings[0].get("link_index") == 2


# ---------------------------------------------------------------------------
# Additional: Healthy bundle has no blocking findings
# ---------------------------------------------------------------------------

class TestHealthyBundleClean:

    def test_healthy_bundle_no_blocking(self, tmp_path):
        bundle = _minimal_bundle(
            tmp_path,
            gate=_minimal_gate(expected_receipt_ids=["r1"]),
            report_verdict="GREEN_FIXTURE",
            receipt_chain=[{"receipt_id": "r1", "record_hash": "h1"}],
            replay={"ok": True, "replay_hash_is_stable": True},
            redaction={"secret_redaction_passed": True},
        )
        _write_json(bundle / "mrec002_manifest.json", {"test": True})
        findings = scan_bundle(bundle)
        assert not any(f.get("blocks_green") for f in findings)

    def test_all_findings_have_neutral_flags(self, tmp_path):
        bundle = _minimal_bundle(
            tmp_path,
            gate=_minimal_gate(phase19_marked_green=True),
            report_verdict="GREEN_FIXTURE",
            receipt_chain=[],
            replay={"ok": False},
            redaction={"secret_redaction_passed": True},
        )
        findings = scan_bundle(bundle)
        assert len(findings) > 0
        for f in findings:
            assert f.get("truth_claimed") is False
            assert f.get("authority_granted") is False
            assert f.get("tools_authorized") is False
            assert f.get("permit_granted") is False
