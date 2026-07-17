"""Public Conformance v0.1: spec, bundle verifier conformance, connector harness, benchmarks."""
from __future__ import annotations

from pathlib import Path


def test_conformance_checker_run(tmp_path: Path) -> None:
    from hg_core.conformance import run_conformance_checks
    (tmp_path / "memory" / "ledger" / "scopes").mkdir(parents=True, exist_ok=True)
    report = run_conformance_checks(tmp_path)
    assert "categories" in report
    assert "A_bundle_integrity" in report["categories"]
    assert "spec_version" in report
    assert report["spec_version"] == "v0.1"


def test_bundle_verify_with_conformance_flag(tmp_path: Path) -> None:
    from hg_core.offline import verify_bundle
    (tmp_path / "memory" / "ledger" / "scopes").mkdir(parents=True, exist_ok=True)
    report = verify_bundle(tmp_path, conformance=True)
    assert "checks" in report
    assert "conformance_v01" in report["checks"]


def test_connector_runner_no_manifest() -> None:
    from hg_core.conformance import load_connector_manifest, run_connector_conformance
    manifest = load_connector_manifest(Path("nonexistent.json"))
    report = run_connector_conformance(manifest)
    assert report["result"] in ("pass", "fail")
    assert "tests" in report


def test_connector_runner_with_manifest(tmp_path: Path) -> None:
    import json
    from hg_core.conformance import load_connector_manifest, run_connector_conformance
    (tmp_path / "connector_manifest.json").write_text(
        json.dumps({"operations": ["op1"], "receipt_fields": ["receipt_id", "hash"], "idempotency": True, "deny_proof_refs": True}),
        encoding="utf-8",
    )
    manifest = load_connector_manifest(tmp_path / "connector_manifest.json")
    report = run_connector_conformance(manifest)
    assert report["result"] == "pass"


def test_benchmark_scenarios_load() -> None:
    from hg_core.conformance import load_scenarios, load_rubric
    scenarios = load_scenarios()
    rubric = load_rubric()
    assert isinstance(scenarios, list)
    assert rubric.get("total") == 100


def test_benchmark_runner_produces_report(tmp_path: Path) -> None:
    from hg_core.conformance import run_benchmarks
    report = run_benchmarks(tmp_path)
    assert "version" in report
    assert "total_score" in report
    assert "scenarios" in report
