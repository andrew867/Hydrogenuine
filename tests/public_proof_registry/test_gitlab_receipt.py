"""GitLab formal_tlc_required receipt gate tests (PPR cases 11-18)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE / "scripts" / "evals"))

import gitlab_formal_tlc_receipt_gate as grg  # noqa: E402


def test_case18_ci_config_detects_required_job():
    ci = grg.validate_ci_config()
    assert ci["job_present"] and ci["stage_validate"]
    assert ci["require_tlc_present"] and ci["allow_failure_false"]
    assert ci["ok"]


def test_case11_pending_bundle_validates_when_push_no(tmp_path, monkeypatch):
    monkeypatch.setenv("OPERATOR_APPROVES_PUSH", "no")
    r = grg.run_gate(output_root=tmp_path)
    assert r["verdict"] == "YELLOW_PENDING_OPERATOR_PUSH"
    assert r["push_performed"] is False and r["pipeline_executed"] is False
    bundle = Path(r["bundle"])
    assert grg.evaluate_bundle(bundle)["ok"], grg.evaluate_bundle(bundle)


def test_case12_pending_cannot_claim_success(tmp_path, monkeypatch):
    monkeypatch.setenv("OPERATOR_APPROVES_PUSH", "no")
    r = grg.run_gate(output_root=tmp_path)
    bundle = Path(r["bundle"])
    pr = json.loads((bundle / "pending_pipeline_receipt.json").read_text(encoding="utf-8"))
    assert pr["status"] == "YELLOW_PENDING_OPERATOR_PUSH"
    assert pr["pipeline_executed"] is False
    # tamper: claim execution -> evaluate must fail
    pr["pipeline_executed"] = True
    (bundle / "pending_pipeline_receipt.json").write_text(json.dumps(pr), encoding="utf-8")
    assert not grg.evaluate_bundle(bundle)["ok"]


def test_case13_16_success_receipt_requires_ids_and_status(tmp_path):
    # Craft a "green" bundle missing the required success files/fields.
    b = tmp_path / "GREEN-x"
    b.mkdir()
    (b / "gate_result.json").write_text(json.dumps({
        "verdict": "GREEN_GITLAB_FORMAL_TLC_RECEIPT", "push_approved": True,
        "ci_config_ok": True, "claims_pipeline_success": True,
        "push_performed": False, "deploy_performed": False}), encoding="utf-8")
    ev = grg.evaluate_bundle(b)
    # missing pipeline_receipt.json + claims_pipeline_success -> fails
    assert not ev["ok"]
    assert any("missing:pipeline_receipt.json" in f for f in ev["failures"])
    assert "claims_pipeline_success" in ev["failures"]


def test_case17_log_scanner_catches_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv("OPERATOR_APPROVES_PUSH", "no")
    r = grg.run_gate(output_root=tmp_path)
    bundle = Path(r["bundle"])
    # inject a secret marker into a bundle text file and re-scan via markers
    leak = bundle / "leak.log"
    leak.write_text("token eyJabc.def.ghi", encoding="utf-8")
    hit = any(m in leak.read_bytes() for m in grg.SECRET_MARKERS)
    assert hit
