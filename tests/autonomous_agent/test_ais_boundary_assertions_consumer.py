"""AIS boundary assertions consumer tests.

Tests that AIS record health scanner correctly consumes boundary_assertions.json
and detects missing, malformed, contradictory, and laundering assertions.

Boundary assertion existence is not truth. Boundary assertion existence is not authority.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hg_runtime.agent_immune_system.boundary_assertions_scanner import (
    REQUIRED_FALSE_ASSERTIONS,
    REQUIRED_TRUE_ASSERTIONS,
    scan_boundary_assertions,
)
from hg_runtime.agent_immune_system.record_health import scan_bundle


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _minimal_gate(verdict: str = "GREEN_FIXTURE", **overrides) -> dict:
    data = {
        "ok": True,
        "verdict": verdict,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
    }
    data.update(overrides)
    return data


def _clean_boundary_assertions() -> dict:
    ba = {}
    for key in REQUIRED_TRUE_ASSERTIONS:
        ba[key] = True
    for key in REQUIRED_FALSE_ASSERTIONS:
        ba[key] = False
    return ba


def _make_bundle(tmp_path: Path, *, gate=None, boundary=None, write_gate=True, write_boundary=True):
    bundle = tmp_path / "test_bundle"
    if write_gate:
        _write_json(bundle / "gate_result.json", gate or _minimal_gate())
    if write_boundary and boundary is not None:
        _write_json(bundle / "boundary_assertions.json", boundary)
    elif write_boundary and boundary is None:
        _write_json(bundle / "boundary_assertions.json", _clean_boundary_assertions())
    return bundle


# ---------------------------------------------------------------------------
# Missing / malformed
# ---------------------------------------------------------------------------

class TestBoundaryAssertionsMissing:

    def test_missing_detected_when_gate_exists(self, tmp_path):
        bundle = _make_bundle(tmp_path, write_boundary=False)
        findings = scan_boundary_assertions(bundle)
        assert any(f["finding_type"] == "missing_boundary_assertions" for f in findings)
        assert not any(f.get("blocks_green") for f in findings)

    def test_missing_not_detected_when_gate_absent(self, tmp_path):
        bundle = tmp_path / "test_bundle"
        bundle.mkdir(parents=True)
        findings = scan_boundary_assertions(bundle)
        assert len(findings) == 0


class TestBoundaryAssertionsMalformed:

    def test_invalid_json_detected(self, tmp_path):
        bundle = _make_bundle(tmp_path, write_boundary=False)
        ba_path = bundle / "boundary_assertions.json"
        ba_path.parent.mkdir(parents=True, exist_ok=True)
        ba_path.write_text("{bad json", encoding="utf-8")
        findings = scan_boundary_assertions(bundle)
        assert any(f["finding_type"] == "malformed_boundary_assertions" for f in findings)
        assert any(f.get("blocks_green") for f in findings)

    def test_non_dict_json_detected(self, tmp_path):
        bundle = _make_bundle(tmp_path, write_boundary=False)
        ba_path = bundle / "boundary_assertions.json"
        ba_path.parent.mkdir(parents=True, exist_ok=True)
        ba_path.write_text("[1, 2, 3]", encoding="utf-8")
        findings = scan_boundary_assertions(bundle)
        assert any(f["finding_type"] == "malformed_boundary_assertions" for f in findings)


# ---------------------------------------------------------------------------
# Required true assertions
# ---------------------------------------------------------------------------

class TestRequiredTrueAssertions:

    def test_missing_required_true_detected(self, tmp_path):
        ba = _clean_boundary_assertions()
        del ba["phase19_yellow_preserved"]
        bundle = _make_bundle(tmp_path, boundary=ba)
        findings = scan_boundary_assertions(bundle)
        missing = [f for f in findings if f["finding_type"] == "boundary_assertion_missing_required"
                   and f.get("assertion_key") == "phase19_yellow_preserved"]
        assert len(missing) == 1

    def test_phase19_false_is_panic_laundering(self, tmp_path):
        ba = _clean_boundary_assertions()
        ba["phase19_yellow_preserved"] = False
        bundle = _make_bundle(tmp_path, boundary=ba)
        findings = scan_boundary_assertions(bundle)
        phase = [f for f in findings if f.get("assertion_key") == "phase19_yellow_preserved"]
        assert len(phase) == 1
        assert phase[0]["severity"] == "PANIC"
        assert phase[0]["finding_type"] == "boundary_assertion_phase_laundering"
        assert phase[0]["blocks_green"] is True

    def test_phase24_false_is_panic_laundering(self, tmp_path):
        ba = _clean_boundary_assertions()
        ba["phase24_infrastructure_only_preserved"] = False
        bundle = _make_bundle(tmp_path, boundary=ba)
        findings = scan_boundary_assertions(bundle)
        phase = [f for f in findings if f.get("assertion_key") == "phase24_infrastructure_only_preserved"]
        assert len(phase) == 1
        assert phase[0]["severity"] == "PANIC"
        assert phase[0]["finding_type"] == "boundary_assertion_phase_laundering"

    def test_no_live_effects_false_is_red(self, tmp_path):
        ba = _clean_boundary_assertions()
        ba["no_live_effects"] = False
        bundle = _make_bundle(tmp_path, boundary=ba)
        findings = scan_boundary_assertions(bundle)
        live = [f for f in findings if f.get("assertion_key") == "no_live_effects"]
        assert len(live) == 1
        assert live[0]["severity"] == "RED"
        assert live[0]["finding_type"] == "boundary_assertion_safety_violation"

    def test_no_tool_authorization_false_detected(self, tmp_path):
        ba = _clean_boundary_assertions()
        ba["no_tool_authorization"] = False
        bundle = _make_bundle(tmp_path, boundary=ba)
        findings = scan_boundary_assertions(bundle)
        assert any(f.get("assertion_key") == "no_tool_authorization" for f in findings)

    def test_no_external_provider_false_detected(self, tmp_path):
        ba = _clean_boundary_assertions()
        ba["no_external_provider_calls"] = False
        bundle = _make_bundle(tmp_path, boundary=ba)
        findings = scan_boundary_assertions(bundle)
        assert any(f.get("assertion_key") == "no_external_provider_calls" for f in findings)

    def test_no_hg_local_access_false_detected(self, tmp_path):
        ba = _clean_boundary_assertions()
        ba["no_hg_local_access"] = False
        bundle = _make_bundle(tmp_path, boundary=ba)
        findings = scan_boundary_assertions(bundle)
        assert any(f.get("assertion_key") == "no_hg_local_access" for f in findings)


# ---------------------------------------------------------------------------
# Required false assertions
# ---------------------------------------------------------------------------

class TestRequiredFalseAssertions:

    def test_model_output_truth_laundering(self, tmp_path):
        ba = _clean_boundary_assertions()
        ba["model_output_treated_as_truth"] = True
        bundle = _make_bundle(tmp_path, boundary=ba)
        findings = scan_boundary_assertions(bundle)
        mot = [f for f in findings if f.get("assertion_key") == "model_output_treated_as_truth"]
        assert len(mot) == 1
        assert mot[0]["severity"] == "RED"
        assert mot[0]["blocks_green"] is True

    def test_local_inference_authority_laundering(self, tmp_path):
        ba = _clean_boundary_assertions()
        ba["local_inference_treated_as_authority"] = True
        bundle = _make_bundle(tmp_path, boundary=ba)
        findings = scan_boundary_assertions(bundle)
        assert any(f.get("assertion_key") == "local_inference_treated_as_authority" for f in findings)

    def test_recommendation_permission_laundering(self, tmp_path):
        ba = _clean_boundary_assertions()
        ba["recommendations_treated_as_permission"] = True
        bundle = _make_bundle(tmp_path, boundary=ba)
        findings = scan_boundary_assertions(bundle)
        assert any(f.get("assertion_key") == "recommendations_treated_as_permission" for f in findings)

    def test_proof_bundle_existence_truth_laundering(self, tmp_path):
        ba = _clean_boundary_assertions()
        ba["proof_bundle_existence_treated_as_truth"] = True
        bundle = _make_bundle(tmp_path, boundary=ba)
        findings = scan_boundary_assertions(bundle)
        assert any(f.get("assertion_key") == "proof_bundle_existence_treated_as_truth" for f in findings)

    def test_tools_authorized_detected(self, tmp_path):
        ba = _clean_boundary_assertions()
        ba["tools_authorized"] = True
        bundle = _make_bundle(tmp_path, boundary=ba)
        findings = scan_boundary_assertions(bundle)
        assert any(f.get("assertion_key") == "tools_authorized" for f in findings)

    def test_live_effects_detected(self, tmp_path):
        ba = _clean_boundary_assertions()
        ba["live_effects_created"] = True
        bundle = _make_bundle(tmp_path, boundary=ba)
        findings = scan_boundary_assertions(bundle)
        assert any(f.get("assertion_key") == "live_effects_created" for f in findings)

    def test_external_provider_calls_detected(self, tmp_path):
        ba = _clean_boundary_assertions()
        ba["external_provider_calls_made"] = True
        bundle = _make_bundle(tmp_path, boundary=ba)
        findings = scan_boundary_assertions(bundle)
        assert any(f.get("assertion_key") == "external_provider_calls_made" for f in findings)

    def test_hg_local_touched_detected(self, tmp_path):
        ba = _clean_boundary_assertions()
        ba["hg_local_touched"] = True
        bundle = _make_bundle(tmp_path, boundary=ba)
        findings = scan_boundary_assertions(bundle)
        assert any(f.get("assertion_key") == "hg_local_touched" for f in findings)

    def test_deployment_permission_panic(self, tmp_path):
        ba = _clean_boundary_assertions()
        ba["deployment_permission_claimed"] = True
        bundle = _make_bundle(tmp_path, boundary=ba)
        findings = scan_boundary_assertions(bundle)
        dep = [f for f in findings if f.get("assertion_key") == "deployment_permission_claimed"]
        assert len(dep) == 1
        assert dep[0]["severity"] == "PANIC"
        assert dep[0]["finding_type"] == "boundary_assertion_laundering_claim"

    def test_agi_claim_panic(self, tmp_path):
        ba = _clean_boundary_assertions()
        ba["agi_claim_made"] = True
        bundle = _make_bundle(tmp_path, boundary=ba)
        findings = scan_boundary_assertions(bundle)
        agi = [f for f in findings if f.get("assertion_key") == "agi_claim_made"]
        assert len(agi) == 1
        assert agi[0]["severity"] == "PANIC"
        assert agi[0]["finding_type"] == "boundary_assertion_laundering_claim"

    def test_missing_required_false_detected(self, tmp_path):
        ba = _clean_boundary_assertions()
        del ba["deployment_permission_claimed"]
        bundle = _make_bundle(tmp_path, boundary=ba)
        findings = scan_boundary_assertions(bundle)
        missing = [f for f in findings if f["finding_type"] == "boundary_assertion_missing_required"
                   and f.get("assertion_key") == "deployment_permission_claimed"]
        assert len(missing) == 1

    def test_remote_llm_calls_detected(self, tmp_path):
        ba = _clean_boundary_assertions()
        ba["remote_llm_calls_made"] = True
        bundle = _make_bundle(tmp_path, boundary=ba)
        findings = scan_boundary_assertions(bundle)
        assert any(f.get("assertion_key") == "remote_llm_calls_made" for f in findings)


# ---------------------------------------------------------------------------
# Laundering claims not in standard set
# ---------------------------------------------------------------------------

class TestExtraLaunderingClaims:

    def test_consciousness_claim_in_required_false_coverage(self, tmp_path):
        """consciousness_claim_made is in LAUNDERING_PANIC_KEYS but not REQUIRED_FALSE."""
        from hg_runtime.agent_immune_system.boundary_assertions_scanner import LAUNDERING_PANIC_KEYS
        assert "consciousness_claim_made" in LAUNDERING_PANIC_KEYS

    def test_sovereignty_claim_in_required_false_coverage(self, tmp_path):
        from hg_runtime.agent_immune_system.boundary_assertions_scanner import LAUNDERING_PANIC_KEYS
        assert "sovereignty_claim_made" in LAUNDERING_PANIC_KEYS


# ---------------------------------------------------------------------------
# Legacy bundle behavior
# ---------------------------------------------------------------------------

class TestLegacyBundleBehavior:

    def test_legacy_bundle_without_boundary_assertions_classified_partial(self, tmp_path):
        """Bundles without boundary_assertions.json get YELLOW (not silent GREEN)."""
        bundle = _make_bundle(tmp_path, write_boundary=False)
        findings = scan_boundary_assertions(bundle)
        missing = [f for f in findings if f["finding_type"] == "missing_boundary_assertions"]
        assert len(missing) == 1
        assert missing[0]["severity"] == "YELLOW"
        assert missing[0]["blocks_green"] is False


# ---------------------------------------------------------------------------
# Clean bundle
# ---------------------------------------------------------------------------

class TestCleanBundle:

    def test_clean_bundle_has_no_findings(self, tmp_path):
        bundle = _make_bundle(tmp_path)
        findings = scan_boundary_assertions(bundle)
        assert len(findings) == 0

    def test_clean_bundle_via_scan_bundle_no_boundary_findings(self, tmp_path):
        bundle = _make_bundle(tmp_path)
        _write_text(bundle / "report_snapshot.md", "## Verdict\n\n`GREEN_FIXTURE`\n")
        _write_json(bundle / "redaction_audit.json", {"secret_redaction_passed": True})
        findings = scan_bundle(bundle)
        boundary_findings = [f for f in findings if "boundary" in f.get("finding_type", "")]
        assert len(boundary_findings) == 0

    def test_all_findings_have_neutral_flags(self, tmp_path):
        ba = _clean_boundary_assertions()
        ba["phase19_yellow_preserved"] = False
        ba["agi_claim_made"] = True
        bundle = _make_bundle(tmp_path, boundary=ba)
        findings = scan_boundary_assertions(bundle)
        assert len(findings) >= 2
        for f in findings:
            assert f.get("truth_claimed") is False
            assert f.get("authority_granted") is False
            assert f.get("tools_authorized") is False
