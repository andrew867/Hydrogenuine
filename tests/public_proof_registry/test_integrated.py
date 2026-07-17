"""Integrated gate self-tests (PPR cases 19-23) — evaluate_bundle + guards."""
from __future__ import annotations

import json
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE / "scripts" / "evals"))

import public_proof_registry_gate as reg_gate  # noqa: E402
import gitlab_formal_tlc_receipt_gate as rcpt_gate  # noqa: E402


def _seal(bundle: Path):
    import hashlib
    files = sorted(p for p in bundle.rglob("*") if p.is_file() and p.name != "checksums.sha256")
    (bundle / "checksums.sha256").write_text(
        "\n".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(bundle).as_posix()}"
                  for p in files) + "\n", encoding="utf-8")


def test_case19_registry_gate_evaluate_fails_on_missing_files(tmp_path):
    b = tmp_path / "empty"
    b.mkdir()
    assert not reg_gate.evaluate_bundle(b)["ok"]


def test_case20_receipt_gate_evaluate_fails_on_missing(tmp_path):
    b = tmp_path / "empty2"
    b.mkdir()
    assert not rcpt_gate.evaluate_bundle(b)["ok"]


def test_case21_registry_gate_flags_stale_or_incomplete_flags(tmp_path):
    # a gate_result asserting failure flags must not evaluate GREEN
    b = tmp_path / "reg"
    (b / "screenshots").mkdir(parents=True)
    for n in ("manifest.json", "registry_reference.json"):
        (b / n).write_text("{}", encoding="utf-8")
    (b / "summary_report.md").write_text("local harness; not a production deployment\n", encoding="utf-8")
    (b / "gate_result.json").write_text(json.dumps({
        "verdict": "GREEN_PUBLIC_PROOF_REGISTRY", "public_ready_ok": True,
        "checksums_ok": False, "claim_boundary_ok": True, "schema_ok": True}), encoding="utf-8")
    _seal(b)
    ev = reg_gate.evaluate_bundle(b)
    assert not ev["ok"] and "checksums_ok_false" in ev["failures"]


def test_case23_write_result_guard_present_in_gates():
    for name in ("public_proof_registry_gate.py", "gitlab_formal_tlc_receipt_gate.py"):
        src = (WORKSPACE / "scripts/evals" / name).read_text(encoding="utf-8")
        assert "refusing to write result inside the sealed bundle" in src


def test_case22_receipt_gate_pending_is_yellow_not_green(tmp_path, monkeypatch):
    monkeypatch.setenv("OPERATOR_APPROVES_PUSH", "no")
    r = rcpt_gate.run_gate(output_root=tmp_path)
    assert r["verdict"].startswith("YELLOW")
    assert r["push_performed"] is False and r["deploy_performed"] is False
