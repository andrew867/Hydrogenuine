"""
Control Surface Pack 5: Public conformance suite — bundle verifier, connector runner, benchmark runner.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from hg_core.conformance import verify_bundle, run_bundle_verify, run_connector_conformance, run_benchmark_scenario


def test_bundle_verify_passes_known_good(tmp_path: Path) -> None:
    """Bundle verifier passes on known-good toy bundle."""
    (tmp_path / "manifests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "bundle.json").write_text(json.dumps({"bundle_id": "b1", "created_ts": "2026-01-01T00:00:00Z"}), encoding="utf-8")
    (tmp_path / "events.jsonl").write_text('{"event_id":"e1","action":"WORK_ITEM_CREATED"}\n', encoding="utf-8")
    (tmp_path / "manifests" / "artifacts_manifest.json").write_text("[]", encoding="utf-8")
    report = verify_bundle(tmp_path)
    assert report.get("result") == "pass"
    assert report.get("bundle_id") == "b1"
    assert any(c.get("id") == "events:jsonl_parse" and c.get("ok") for c in report.get("checks", []))


def test_bundle_verify_fails_tampered_events(tmp_path: Path) -> None:
    """Bundle verifier fails on invalid events.jsonl."""
    (tmp_path / "manifests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "bundle.json").write_text(json.dumps({"bundle_id": "b2"}), encoding="utf-8")
    (tmp_path / "events.jsonl").write_text("not valid json\n", encoding="utf-8")
    (tmp_path / "manifests" / "artifacts_manifest.json").write_text("[]", encoding="utf-8")
    report = verify_bundle(tmp_path)
    assert report.get("result") == "fail"
    assert any(c.get("id") == "events:jsonl_parse" and not c.get("ok") for c in report.get("checks", []))


def test_bundle_verify_fails_missing_bundle_json(tmp_path: Path) -> None:
    """Bundle verifier fails when bundle.json is missing."""
    report = verify_bundle(tmp_path)
    assert report.get("result") == "fail"
    assert any("missing" in str(c.get("id", "")) for c in report.get("checks", []))


def test_run_bundle_verify_writes_report(tmp_path: Path) -> None:
    """run_bundle_verify writes verification_report.json and .txt."""
    (tmp_path / "manifests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "bundle.json").write_text(json.dumps({"bundle_id": "b3"}), encoding="utf-8")
    (tmp_path / "events.jsonl").write_text("{}", encoding="utf-8")
    (tmp_path / "manifests" / "artifacts_manifest.json").write_text("[]", encoding="utf-8")
    report = run_bundle_verify(tmp_path)
    assert (tmp_path / "verification_report.json").exists()
    assert (tmp_path / "verification_report.txt").exists()
    assert report.get("result") == "pass"


def test_connector_conformance_checks_manifest(tmp_path: Path) -> None:
    """Connector conformance checks minimal manifest requirements."""
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"operations": [{}], "data_classes": [{}]}), encoding="utf-8")
    report = run_connector_conformance(manifest)
    assert report.get("result") == "pass"
    assert any(t.get("id") == "manifest:has_operations" and t.get("ok") for t in report.get("tests", []))


def test_connector_conformance_fails_without_operations(tmp_path: Path) -> None:
    """Connector conformance fails when operations missing."""
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"data_classes": []}), encoding="utf-8")
    report = run_connector_conformance(manifest)
    assert report.get("result") == "fail"


def test_connector_conformance_fixture_manifest() -> None:
    """Connector conformance passes on bundled minimal_connector_manifest.json."""
    fixtures_dir = Path(__file__).resolve().parent.parent.parent / "hg_core" / "conformance" / "fixtures"
    manifest_path = fixtures_dir / "minimal_connector_manifest.json"
    if not manifest_path.exists():
        pytest.skip("fixtures not in layout")
    report = run_connector_conformance(manifest_path)
    assert report.get("result") == "pass"


def test_benchmark_runner_with_bundle(tmp_path: Path) -> None:
    """Benchmark scenario runner scores using bundle events."""
    (tmp_path / "manifests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "events.jsonl").write_text('{"event_id":"e1"}\n', encoding="utf-8")
    scenario_path = Path(__file__).resolve().parent.parent.parent / "hg_core" / "conformance" / "fixtures" / "scenario_default.json"
    if not scenario_path.exists():
        pytest.skip("scenario fixture not found")
    report = run_benchmark_scenario(scenario_path, bundle_dir=tmp_path)
    assert "score" in report
    assert "breakdown" in report
    assert report.get("scenario_id") == "default"


def test_benchmark_runner_with_event_stream() -> None:
    """Benchmark scenario runner accepts in-memory event stream."""
    scenario_path = Path(__file__).resolve().parent.parent.parent / "hg_core" / "conformance" / "fixtures" / "scenario_default.json"
    if not scenario_path.exists():
        pytest.skip("scenario fixture not found")
    report = run_benchmark_scenario(scenario_path, event_stream=[{"event_id": "e1"}])
    assert report.get("score", 0) >= 0
    assert report.get("result") in ("pass", "fail")
