"""CT completion gate tests — the 12 required cases.

Run: python -m pytest --import-mode=importlib -q tests/ct_completion
Verdicts are asserted on JSON fields, never process exit codes.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))
sys.path.insert(0, str(WORKSPACE / "scripts" / "evals"))

import connective_tissue_completion_gate as gate  # noqa: E402

os.environ["CT_GATE_NO_SELFTEST"] = "1"  # prevent pytest recursion inside run_gate


def _checks_by_name(checks):
    return {c["name"]: c for c in checks.items}


# 1. Fails on missing matrix
def test_gate_fails_on_missing_matrix(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "MATRIX_PATH", tmp_path / "nope.json")
    result = gate.run_gate(bundle_root=tmp_path / "bundles")
    assert result["verdict"] == "red"
    assert "matrix_present" in result["critical_failures"]


# 2. Fails on missing evidence for a DONE pack
def test_matrix_missing_evidence_fails():
    checks = gate.Checks()
    matrix = {"packs": [{"ct_id": "CT-99", "name": "x", "final_status": "DONE_VERIFIED",
                         "evidence": ["docs/does/not/exist"]}], "meta_items": []}
    gate.check_matrix(matrix, checks)
    named = _checks_by_name(checks)
    assert named["matrix_evidence:CT-99"]["ok"] is False


# 3. Fails if a subsystem gate result is RED
def test_subsystem_red_fails(tmp_path):
    d = tmp_path / "docs/proofs/connective_tissue/pack01/20990101T000000Z"
    d.mkdir(parents=True)
    (d / "gate_result.json").write_text(json.dumps({"gate": "iam", "ok": False}), encoding="utf-8")
    checks = gate.Checks()
    gate.check_subsystem_gates(checks, root=tmp_path)
    named = _checks_by_name(checks)
    assert named["subsystem_gate:pack01"]["ok"] is False


# 4. Reads JSON verdict, not process exit code
def test_obt_verdict_read_from_json(tmp_path):
    d = tmp_path / "20990101T000000Z"
    d.mkdir(parents=True)
    (d / "truth_gate_report.json").write_text(
        json.dumps({"strict_ct_mode": True, "verdict": "red", "head": "abc"}), encoding="utf-8")
    checks = gate.Checks()
    gate.check_obt(checks, pack04_dir=tmp_path)
    assert _checks_by_name(checks)["obt_strict_verdict"]["ok"] is False

    (d / "truth_gate_report.json").write_text(
        json.dumps({"strict_ct_mode": True, "verdict": "green", "head": "abc"}), encoding="utf-8")
    checks2 = gate.Checks()
    gate.check_obt(checks2, pack04_dir=tmp_path)
    assert _checks_by_name(checks2)["obt_strict_verdict"]["ok"] is True


# 5. Orphan/undeclared gate detection (registry supports it)
def test_orphan_gate_detected(tmp_path):
    from hg_core.truth.registry import load_registry
    reg = load_registry()
    # Real evals dir: no orphans after the 2026-07-02 registration pass.
    assert reg.orphan_scripts(WORKSPACE / "scripts" / "evals") == []
    # A synthetic undeclared gate script is detected.
    evals = tmp_path / "evals"
    evals.mkdir()
    (evals / "totally_undeclared_gate.py").write_text("print('{}')", encoding="utf-8")
    assert "totally_undeclared_gate.py" in reg.orphan_scripts(evals)


# 6. Fails on forbidden claims
def test_claim_firewall_forbidden(tmp_path):
    doc = tmp_path / "bad.md"
    doc.write_text("This system is formally verified and tamper-proof.", encoding="utf-8")
    res = gate.claim_firewall_scan([doc])
    assert res["ok"] is False
    assert len(res["violations"]) >= 2


# 6b. Boundary-negated phrasing is allowed
def test_claim_firewall_negation_allowed(tmp_path):
    doc = tmp_path / "ok.md"
    doc.write_text("Receipts are tamper-evident, not tamper-proof. "
                   "Production certified is not claimed.", encoding="utf-8")
    res = gate.claim_firewall_scan([doc])
    assert res["ok"] is True


# 7. Fails if production operator auth is claimed
def test_production_auth_claim_fails(tmp_path):
    doc = tmp_path / "auth.md"
    doc.write_text("Sessions are production operator authenticated.", encoding="utf-8")
    res = gate.claim_firewall_scan([doc])
    assert res["ok"] is False


# 8. Fails if real external execution claimed while UEAK/OEA stubbed
def test_external_execution_claim_fails(tmp_path):
    doc = tmp_path / "exec.md"
    doc.write_text("The runtime performs real external execution of tasks.", encoding="utf-8")
    res = gate.claim_firewall_scan([doc])
    assert res["ok"] is False
    # and the code-side markers still prove the stub boundary
    checks = gate.Checks()
    gate.check_boundaries(checks)
    assert all(c["ok"] for c in checks.items), checks.items


# 9. Fails on tampered checksum
def test_tampered_checksum_detected(tmp_path):
    res = gate.negative_tamper_case(tmp_path / "fixture")
    assert res["clean_verifies"] is True
    assert res["tamper_detected"] is True

    # manifest-level: fabricated pack bundle with wrong recorded hash fails verification
    d = tmp_path / "docs/proofs/connective_tissue/pack01/20990101T000000Z"
    d.mkdir(parents=True)
    (d / "gate_result.json").write_text('{"ok": true}', encoding="utf-8")
    (d / "manifest.json").write_text(
        json.dumps({"file_hashes": {"gate_result.json": "0" * 64}}), encoding="utf-8")
    checks = gate.Checks()
    result = gate.verify_pack_bundle_hashes(checks, root=tmp_path)
    assert any(f.get("reason") == "hash mismatch" for f in result["failures"])


# 10. Writes manifest/checksums/result
def test_gate_writes_bundle(tmp_path):
    result = gate.run_gate(bundle_root=tmp_path / "bundles")
    bundle = WORKSPACE / result["proof_bundle_path"]
    if not bundle.is_absolute() or not bundle.exists():
        bundle = tmp_path / "bundles" / sorted(os.listdir(tmp_path / "bundles"))[-1]
    for name in ["gate_result.json", "manifest.json", "checksums.sha256",
                 "ct_completion_matrix.json", "ct_completion_summary.md",
                 "tests_result.json", "claim_firewall_result.json",
                 "proof_integrity_result.json", "negative_tamper_case_result.json",
                 "planner_update_result.json", "subagent_reports_index.json"]:
        assert (bundle / name).is_file(), f"missing {name}"
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    assert "gate_result.json" in manifest["file_hashes"]


# 11. Allows honest YELLOW with explicit caveat
def test_honest_yellow_with_caveat():
    checks = gate.Checks()
    matrix = {"expected_pack_count": 1,
              "packs": [{"ct_id": "CT-11", "name": "time", "final_status": "DONE_WITH_CAVEAT",
                         "evidence": ["workspace/docs/planning/connective_tissue/CT-INVARIANTS.md"],
                         "caveat": "U4 slice only; full TIM suite deferred. Planner-linked."}],
              "meta_items": []}
    caveats = gate.check_matrix(matrix, checks)
    assert not checks.critical_failures
    assert caveats and caveats[0]["ct_id"] == "CT-11"
    # a DONE_WITH_CAVEAT without a caveat is NOT allowed
    checks2 = gate.Checks()
    matrix["packs"][0]["caveat"] = None
    gate.check_matrix(matrix, checks2)
    assert "matrix_caveat_explicit:CT-11" in checks2.critical_failures


# 12. Passes on the real, completed CT matrix
def test_real_matrix_classifies_all_packs():
    matrix = gate.load_matrix()
    checks = gate.Checks()
    gate.check_matrix(matrix, checks)
    matrix_failures = [n for n in checks.critical_failures if n.startswith("matrix")]
    assert matrix_failures == [], matrix_failures
    assert len(matrix["packs"]) == 17
    statuses = {r["final_status"] for r in matrix["packs"]}
    assert statuses <= gate.ALLOWED_STATUSES
