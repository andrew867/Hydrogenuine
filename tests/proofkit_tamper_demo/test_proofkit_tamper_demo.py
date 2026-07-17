"""Proofkit tamper demo tests — the 15 required cases.

Run: python -m pytest --import-mode=importlib -q tests/proofkit_tamper_demo
Assertions read JSON verdict fields, never exit codes.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
OUTER = WORKSPACE.parent
sys.path.insert(0, str(WORKSPACE))
sys.path.insert(0, str(WORKSPACE / "scripts" / "evals"))
sys.path.insert(0, str(OUTER / "hydrogenuine-proofkit" / "tools"))

try:
    from _common import receipt_hash  # noqa: E402  (proofkit canonical hash)
except ModuleNotFoundError:
    pytest.skip("external hydrogenuine-proofkit tooling (_common) not checked out",
                allow_module_level=True)
from hg_runtime.demos.proofkit_tamper_demo.harness import run_demo, tree_hash  # noqa: E402
from hg_runtime.demos.proofkit_tamper_demo.reports import seal_bundle, write_reports  # noqa: E402
import proofkit_tamper_demo_gate as gate  # noqa: E402

REAL_SOURCE = WORKSPACE / "docs/proofs/governed_research_soak/operator_ui_live"
REAL_DEMO_BUNDLE_ROOT = OUTER / "docs/proofs/proofkit_tamper_demo"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def make_fixture_source(root: Path) -> Path:
    """Minimal proofkit-compatible live-tier bundle with valid hashes/checksums."""
    src = root / "fixture_source"
    src.mkdir(parents=True)
    head = "deadbeef" * 5
    (src / "HEAD.txt").write_text(head + "\n", encoding="utf-8")
    for name, payload in {
        "session_receipt.json": {"schema_version": "1", "receipt_id": "r1",
                                 "question": "what is tested", "data_tier": "live"},
        "quality_gate_receipt.json": {"schema_version": "1", "receipt_id": "r2",
                                      "outcome": "held", "data_tier": "live"},
    }.items():
        payload["hash"] = receipt_hash(payload)
        (src / name).write_text(json.dumps(payload, indent=1), encoding="utf-8")
    (src / "demo_config.json").write_text(json.dumps(
        {"demo": "fixture-of-the-tamper-demo-tests", "data_tier": "live",
         "fixture_label": None}, indent=1), encoding="utf-8")
    (src / "gate_result.json").write_text(json.dumps(
        {"verdict": "GREEN_FIXTURE_SOURCE", "head": head}, indent=1), encoding="utf-8")
    (src / "summary_report.md").write_text("# Fixture source summary\n", encoding="utf-8")
    files = ["HEAD.txt", "session_receipt.json", "quality_gate_receipt.json",
             "demo_config.json", "gate_result.json", "summary_report.md",
             "checksums.sha256", "manifest.json"]
    lines = [f"{_sha(src / f)}  {f}" for f in files if f not in ("checksums.sha256", "manifest.json")]
    (src / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (src / "manifest.json").write_text(json.dumps(
        {"schema_version": "1", "verdict": "GREEN_FIXTURE_SOURCE", "head": head,
         "data_tier": "live", "files": files}, indent=1), encoding="utf-8")
    return src


@pytest.fixture(scope="module")
def demo_run(tmp_path_factory):
    root = tmp_path_factory.mktemp("pkt")
    src = make_fixture_source(root)
    before = tree_hash(src)
    result = run_demo(src, root / "out", public_safe=True)
    out = Path(result["output_dir"])
    write_reports(out, result)
    seal_bundle(out)
    return {"src": src, "before": before, "result": result, "out": out}


def _case(result, cid):
    return next(c for c in result["case_results"] if c["case_id"] == cid)


# 1. Harness does not mutate the source bundle
def test_source_not_mutated(demo_run):
    assert demo_run["result"]["source_bundle_unchanged"] is True
    assert tree_hash(demo_run["src"]) == demo_run["before"]


# 2. Baseline validation passes on the fixture
def test_baseline_passes(demo_run):
    assert demo_run["result"]["baseline_ok"] is True


# 3–7. Each tamper case fails for the expected reason
def test_receipt_hash_mismatch_fails(demo_run):
    c = _case(demo_run["result"], "receipt_hash_mismatch")
    assert c["actual_verdict"] == "RED_RECEIPT_HASH_INVALID"
    assert c["expected_failure_matched"] is True


def test_checksum_mismatch_fails(demo_run):
    c = _case(demo_run["result"], "manifest_checksum_mismatch")
    assert c["actual_verdict"] == "RED_CHECKSUM_VERIFICATION_FAILED"
    assert c["expected_failure_matched"] is True


def test_missing_artifact_fails(demo_run):
    c = _case(demo_run["result"], "missing_required_artifact")
    assert "RED" in c["actual_verdict"]
    assert c["expected_failure_matched"] is True


def test_fixture_leak_fails(demo_run):
    c = _case(demo_run["result"], "fixture_leak_in_live_bundle")
    assert c["actual_verdict"] == "RED_FIXTURE_LEAK_DETECTED"
    assert c["expected_failure_matched"] is True


def test_gate_inconsistency_fails(demo_run):
    c = _case(demo_run["result"], "gate_result_inconsistency")
    assert c["expected_failure_matched"] is True


def _mutate_and_gate(demo_run, tmp_path, mutator):
    import shutil
    b = tmp_path / "bundle"
    shutil.copytree(demo_run["out"], b)
    mutator(b)
    seal_bundle(b)  # reseal so only the intended condition differs
    return gate.run_gate(b, write_result=tmp_path / "res.json")


# 8. Gate fails if baseline fails
def test_gate_red_on_baseline_failure(demo_run, tmp_path):
    def mut(b):
        d = json.loads((b / "baseline_validation_result.json").read_text(encoding="utf-8"))
        d["baseline_ok"] = False
        (b / "baseline_validation_result.json").write_text(json.dumps(d), encoding="utf-8")
    r = _mutate_and_gate(demo_run, tmp_path, mut)
    assert r["verdict"].startswith("RED")
    assert r["baseline_ok"] is False


# 9. Gate fails if a tampered case unexpectedly passes
def test_gate_red_on_unexpected_pass(demo_run, tmp_path):
    def mut(b):
        d = json.loads((b / "tamper_case_results.json").read_text(encoding="utf-8"))
        for c in d:
            if c["case_id"] == "receipt_hash_mismatch":
                c["expected_failure_matched"] = False
                c["actual_verdict"] = "GREEN_RECEIPT_HASHES_VALID"
        (b / "tamper_case_results.json").write_text(json.dumps(d), encoding="utf-8")
    r = _mutate_and_gate(demo_run, tmp_path, mut)
    assert r["verdict"].startswith("RED")


# 10. Gate fails if the source bundle hash changed
def test_gate_red_on_source_hash_change(demo_run, tmp_path):
    def mut(b):
        d = json.loads((b / "source_bundle_summary.json").read_text(encoding="utf-8"))
        d["tree_sha256_after"] = "0" * 64
        (b / "source_bundle_summary.json").write_text(json.dumps(d), encoding="utf-8")
    r = _mutate_and_gate(demo_run, tmp_path, mut)
    assert r["verdict"].startswith("RED")
    assert r["source_bundle_unchanged"] is False


# 11. Gate fails on assertive "tamper-proof" wording
def test_gate_red_on_tamper_proof_claim(demo_run, tmp_path):
    def mut(b):
        p = b / "summary_report.md"
        p.write_text(p.read_text(encoding="utf-8") +
                     "\nOur storage is tamper-proof and immune to modification.\n",
                     encoding="utf-8")
    r = _mutate_and_gate(demo_run, tmp_path, mut)
    assert r["verdict"].startswith("RED")
    assert r["claim_boundary_ok"] is False


# 12. Gate fails on model-correctness claim
def test_gate_red_on_model_correctness_claim(demo_run, tmp_path):
    def mut(b):
        p = b / "summary_report.md"
        p.write_text(p.read_text(encoding="utf-8") +
                     "\nThis demo proves model correctness for all outputs.\n",
                     encoding="utf-8")
    r = _mutate_and_gate(demo_run, tmp_path, mut)
    assert r["verdict"].startswith("RED")


# 13. Demo + gate write manifest/checksums/proof_index/result
def test_outputs_written(demo_run, tmp_path):
    out = demo_run["out"]
    for name in ["manifest.json", "checksums.sha256", "proof_index.json",
                 "summary_report.md", "claim_boundary_report.md", "website_handoff.md",
                 "demo_report.html", "tamper_case_results.json"]:
        assert (out / name).is_file(), name
    r = gate.run_gate(out, write_result=tmp_path / "gate.json")
    assert (tmp_path / "gate.json").is_file()
    assert r["verdict"].startswith(("GREEN", "YELLOW"))


# 14. Honest YELLOW when only an optional case is unsupported (documented)
def test_gate_yellow_on_optional_case_unsupported(demo_run, tmp_path):
    def mut(b):
        d = json.loads((b / "tamper_case_results.json").read_text(encoding="utf-8"))
        for c in d:
            if c["case_id"] == "fixture_leak_in_live_bundle":
                c["expected_failure_matched"] = False
                c["actual_verdict"] = "YELLOW_DETECTOR_UNSUPPORTED_DOCUMENTED"
        (b / "tamper_case_results.json").write_text(json.dumps(d), encoding="utf-8")
    r = _mutate_and_gate(demo_run, tmp_path, mut)
    assert r["verdict"].startswith("YELLOW"), r["verdict"]


# 15. End-to-end GREEN with the real source bundle (when present)
def test_real_bundle_gate_green(tmp_path):
    if not REAL_SOURCE.is_dir() or not REAL_DEMO_BUNDLE_ROOT.is_dir():
        pytest.skip("real GRS source or demo bundle not present")
    bundles = sorted(d for d in REAL_DEMO_BUNDLE_ROOT.iterdir() if d.is_dir())
    assert bundles, "no real tamper-demo bundle produced yet"
    # Write the fresh result OUTSIDE the committed bundle — sealed bundles are
    # read-only; re-verification must never rewrite them in place.
    r = gate.run_gate(bundles[-1], write_result=tmp_path / "gate_result.json")
    assert r["verdict"] == "GREEN_PROOFKIT_TAMPER_DEMO", r["verdict"]
    assert r["source_bundle_unchanged"] is True
