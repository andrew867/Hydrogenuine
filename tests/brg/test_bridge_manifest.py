"""CT-08 BRG bridge manifest and gate validation tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hg_core.product_bridge.manifest import (
    INTEGRATED_CLAIMS,
    load_manifest,
    manifest_hash,
)
from hg_core.product_bridge.plt_crosscheck import crosscheck_plt_statuses, plt_crosscheck_ok
from hg_core.product_bridge.validator import findings_ok, validate_manifest

WORKSPACE = Path(__file__).resolve().parents[2]


def test_bridge_manifest_schema_validates() -> None:
    manifest = load_manifest(workspace=WORKSPACE)
    assert manifest.schema == "product_organism_bridge_manifest_v1"
    assert len(manifest.surfaces) >= 8
    assert len(manifest.capability_cards) >= 4
    payload = manifest.to_payload()
    assert manifest_hash(payload) == manifest.manifest_hash


def _write_manifest(tmp_path: Path, payload: dict) -> Path:
    payload["manifest_hash"] = manifest_hash(payload)
    broken_path = tmp_path / "broken_manifest.json"
    broken_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return broken_path


def test_missing_evidence_fails_validation(tmp_path: Path) -> None:
    manifest = load_manifest(workspace=WORKSPACE)
    payload = manifest.to_payload()
    payload["surfaces"][0]["evidence_path"] = "docs/proofs/does_not_exist_xyz"
    payload["surfaces"][0]["evidence_status"] = "present"
    broken = load_manifest(_write_manifest(tmp_path, payload), workspace=WORKSPACE)
    findings = validate_manifest(broken, workspace=WORKSPACE)
    assert not findings_ok(findings)
    assert any(f.check == "surface_evidence" and f.verdict == "fail" for f in findings)


def test_stub_surface_cannot_be_labeled_integrated(tmp_path: Path) -> None:
    manifest = load_manifest(workspace=WORKSPACE)
    payload = manifest.to_payload()
    for surface in payload["surfaces"]:
        if surface["organism_subsystem"] == "OEA":
            surface["status"] = "STUB"
            surface["integration_claim"] = "integrated"
            break
    with pytest.raises(ValueError, match="stub/scaffold surface cannot claim integrated"):
        load_manifest(_write_manifest(tmp_path, payload), workspace=WORKSPACE)


def test_product_claim_must_cite_proof_or_test_or_report(tmp_path: Path) -> None:
    manifest = load_manifest(workspace=WORKSPACE)
    payload = manifest.to_payload()
    payload["capability_cards"][0]["product_claim"] = "Everything is fully integrated with no citations."
    with pytest.raises(ValueError, match="product_claim missing citation"):
        load_manifest(_write_manifest(tmp_path, payload), workspace=WORKSPACE)


def test_plt_read_path_status_matches_backend() -> None:
    manifest = load_manifest(workspace=WORKSPACE)
    results = crosscheck_plt_statuses(manifest, workspace=WORKSPACE)
    assert results
    assert plt_crosscheck_ok(results)
    for result in results:
        assert result.match, f"{result.plt_subsystem_key}: {result.manifest_status} != {result.backend_status}"


def test_fake_green_claims_fail(tmp_path: Path) -> None:
    manifest = load_manifest(workspace=WORKSPACE)
    payload = manifest.to_payload()
    payload["capability_cards"][0]["status"] = "STUB"
    payload["capability_cards"][0]["integration_claim"] = "integrated"
    with pytest.raises(ValueError, match="capability card cannot claim integrated"):
        load_manifest(_write_manifest(tmp_path, payload), workspace=WORKSPACE)


def test_integrated_claims_subset() -> None:
    manifest = load_manifest(workspace=WORKSPACE)
    for surface in manifest.surfaces:
        if surface.status == "STUB":
            assert surface.integration_claim not in INTEGRATED_CLAIMS
