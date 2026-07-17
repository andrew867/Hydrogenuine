"""CT-04 OBT unit and integration tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
GATE = WORKSPACE / "scripts" / "evals" / "hg_full_truth_gate.py"

from hg_core.truth.classify import classify_subsystems_truth, static_stub_scan  # noqa: E402
from hg_core.truth.registry import load_registry  # noqa: E402
from hg_core.truth.report import build_report, seal_bundle_hash  # noqa: E402


def test_obt_u1_registry_loads_no_orphans() -> None:
    registry = load_registry()
    orphans = registry.orphan_scripts(WORKSPACE / "scripts" / "evals")
    assert orphans == [], f"orphan gates: {orphans}"
    assert registry.registry_hash.startswith("sha256:")
    assert len(registry.gates) >= 35


def test_obt_u1_orphan_detection_fails_closed(tmp_path: Path) -> None:
    registry = load_registry()
    evals = tmp_path / "evals"
    evals.mkdir()
    (evals / "orphan_gate.py").write_text("# orphan\n", encoding="utf-8")
    orphans = registry.orphan_scripts(evals)
    assert "orphan_gate.py" in orphans


@pytest.mark.obt_integration
def test_obt_u2_dirty_without_allow_dirty_fails() -> None:
    result = subprocess.run(
        [sys.executable, str(GATE), "--fast", "--json"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        pytest.skip("worktree clean — dirty check path not exercised")
    report = json.loads(result.stdout)
    dirty_stage = next(s for s in report["stages"] if s["stage"] == "git_dirty_check")
    assert dirty_stage["verdict"] == "fail" or report["verdict"] == "red"


def test_obt_u2_allow_dirty_records_dirt() -> None:
    result = subprocess.run(
        [sys.executable, str(GATE), "--fast", "--allow-dirty", "--json"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    assert result.returncode in {0, 1, 2}
    report = json.loads(result.stdout)
    assert report.get("allow_dirty") is True
    assert "dirty_files" in report


@pytest.mark.obt_integration
def test_obt_u3_skip_appears_in_report() -> None:
    registry = load_registry()
    deferred = [g for g in registry.gates if g.run_policy == "deferred" and g.enabled]
    assert deferred, "expected deferred gates in registry"
    result = subprocess.run(
        [sys.executable, str(GATE), "--fast", "--allow-dirty", "--json"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    report = json.loads(result.stdout)
    assert report["skips"], "deferred gates must appear as skips"
    if report["skips"]:
        assert report["verdict"] != "green"


def test_obt_u4_injected_failing_gate_red() -> None:
    report = build_report(
        head="abc",
        path_ids=["connective_tissue/pack04"],
        stages=[{"stage": "proof_gates", "verdict": "fail"}],
        gate_results=[{"gate_id": "iam_authority", "verdict": "fail", "critical": True}],
        subsystem_classification=[],
        skips=[],
        fast_subset=False,
        allow_dirty=False,
        dirty_files=[],
        registry_hash="sha256:" + "a" * 64,
        critical_failures=["iam_authority"],
    )
    assert report.verdict == "red"


def test_obt_u5_stub_scan_flips_classification(tmp_path: Path) -> None:
    mod = tmp_path / "hg_runtime" / "fake_sub"
    mod.mkdir(parents=True)
    (mod / "stub_module.py").write_text("raise NotImplementedError\n", encoding="utf-8")
    findings = static_stub_scan(tmp_path, roots=("hg_runtime",))
    assert "hg_runtime/fake_sub/stub_module.py" in findings
    rows = classify_subsystems_truth(workspace=tmp_path, static_findings=findings)
    assert any(r["status"] == "stubbed" for r in rows)


def test_obt_u6_bundle_hash_matches_sealed_bundle(tmp_path: Path) -> None:
    proof = tmp_path / "bundle"
    proof.mkdir()
    (proof / "truth_gate_report.json").write_text('{"schema":"truth_gate_report_v1"}', encoding="utf-8")
    digest = seal_bundle_hash(proof)
    assert digest.startswith("sha256:")
    assert len(digest) == 71


def test_obt_u7_fast_cannot_produce_plain_green() -> None:
    result = subprocess.run(
        [sys.executable, str(GATE), "--fast", "--allow-dirty", "--json"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    report = json.loads(result.stdout)
    assert report["fast_subset"] is True
    assert report["verdict"] in {"green_fast", "red"}
    assert report["verdict"] != "green"


@pytest.mark.obt_integration
def test_obt_proof_bundle_generated() -> None:
    result = subprocess.run(
        [sys.executable, str(GATE), "--fast", "--allow-dirty"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    summary = json.loads(result.stdout)
    proof_dir = Path(summary["proof_dir"])
    assert proof_dir.is_dir()
    assert (proof_dir / "truth_gate_report.json").is_file()
    assert (proof_dir / "manifest.json").is_file()
    assert (proof_dir / "command_log.jsonl").is_file()
    manifest = json.loads((proof_dir / "manifest.json").read_text(encoding="utf-8"))
    report = json.loads((proof_dir / "truth_gate_report.json").read_text(encoding="utf-8"))
    assert manifest["bundle_hash"] == report["bundle_hash"]
