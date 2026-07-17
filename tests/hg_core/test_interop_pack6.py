"""
Interop Pack 6: Reference baselines, formal invariants, demo bundle, taxonomy adapter.
"""
from __future__ import annotations

import json
from pathlib import Path

from hg_core.interop import (
    export_toy_bundle,
    verify_ref_bundle,
    run_invariant_checker,
    internal_action_to_public_class,
)


def test_ref_bundle_exporter_produces_toy_bundle(tmp_path: Path) -> None:
    """Reference components produce a toy bundle (bundle.json, events.jsonl, manifests/)."""
    out = tmp_path / "bundle_out"
    bundle = export_toy_bundle(out)
    assert bundle.get("bundle_id", "").startswith("toy-bundle_")
    assert (out / "bundle.json").is_file()
    assert (out / "events.jsonl").is_file()
    assert (out / "manifests" / "artifacts_manifest.json").is_file()
    with open(out / "events.jsonl", "r", encoding="utf-8") as f:
        lines = [l for l in f if l.strip()]
    assert len(lines) >= 2


def test_ref_bundle_verifier_passes_toy_bundle(tmp_path: Path) -> None:
    """Bundle verifier passes the toy bundle."""
    out = tmp_path / "bundle_out"
    export_toy_bundle(out)
    report = verify_ref_bundle(out)
    assert report.get("ok") is True
    assert report.get("errors") == []


def test_ref_bundle_verifier_fails_missing_file(tmp_path: Path) -> None:
    """Bundle verifier fails when required file missing."""
    (tmp_path / "bundle_out").mkdir()
    (tmp_path / "bundle_out" / "bundle.json").write_text("{}", encoding="utf-8")
    report = verify_ref_bundle(tmp_path / "bundle_out")
    assert report.get("ok") is False
    assert any("missing" in str(e).lower() for e in report.get("errors", []))


def test_invariant_checker_reports_structured_results(tmp_path: Path) -> None:
    """Invariant checker runs and reports structured results."""
    events_path = tmp_path / "events.jsonl"
    events_path.write_text(
        json.dumps({"event_id": "e1", "action": "WORK_ITEM_CREATED", "payload": {}}) + "\n"
        + json.dumps({"event_id": "e2", "action": "SETTLEMENT_PUBLISHED", "payload": {}}) + "\n",
        encoding="utf-8",
    )
    report = run_invariant_checker(events_path)
    assert "invariants" in report
    assert isinstance(report["invariants"], list)
    for inv in report["invariants"]:
        assert "id" in inv
        assert "ok" in inv
    # SETTLEMENT_PUBLISHED without quorum_proof_artifact_id should fail INV-005
    inv005 = next((i for i in report["invariants"] if i.get("id") == "INV-005"), None)
    assert inv005 is not None
    assert inv005.get("ok") is False


def test_invariant_checker_settlement_with_quorum_passes(tmp_path: Path) -> None:
    """Settlement with quorum proof passes INV-005."""
    events_path = tmp_path / "events.jsonl"
    events_path.write_text(
        json.dumps({
            "event_id": "e1",
            "action": "SETTLEMENT_PUBLISHED",
            "payload": {"settlement_id": "s1", "quorum_proof_artifact_id": "/path/to/proof.json"},
        }) + "\n",
        encoding="utf-8",
    )
    report = run_invariant_checker(events_path)
    inv005 = next((i for i in report["invariants"] if i.get("id") == "INV-005"), None)
    assert inv005 is not None
    assert inv005.get("ok") is True


def test_taxonomy_adapter_maps_without_leaking(tmp_path: Path) -> None:
    """Adapters map internal taxonomy to public classes without leaking internals."""
    assert internal_action_to_public_class("CAPABILITY_GRANT_ISSUED") == "CapabilityGrant"
    assert internal_action_to_public_class("SETTLEMENT_PUBLISHED") == "Settlement"
    assert internal_action_to_public_class("DISPUTE_OPENED") == "Dispute"
    # Unknown action returns None (do not leak internal name)
    assert internal_action_to_public_class("INTERNAL_DEBUG_EVENT") is None


def test_demo_e2e_toy_bundle_verify_and_invariant(tmp_path: Path) -> None:
    """Demo: export toy bundle, verify it, run invariant checker (e2e)."""
    out = tmp_path / "demo_bundle"
    export_toy_bundle(out)
    verify_report = verify_ref_bundle(out)
    assert verify_report.get("ok") is True
    inv_report = run_invariant_checker(out / "events.jsonl")
    assert "invariants" in inv_report
    # Toy bundle has no settlement/downgrade/grant so most invariants pass or are N/A
    assert isinstance(inv_report["invariants"], list)
