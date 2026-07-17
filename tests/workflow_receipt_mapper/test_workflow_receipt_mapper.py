"""Workflow receipt mapper tests — the 18 required cases.

Run: python -m pytest --import-mode=importlib -q tests/workflow_receipt_mapper
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))
sys.path.insert(0, str(WORKSPACE / "scripts" / "evals"))

from hg_runtime.workflow_receipt_mapper import mapper as M  # noqa: E402
from hg_runtime.workflow_receipt_mapper.schema import (  # noqa: E402
    IntakeError, load_intake, scan_for_secrets, validate_intake,
)
import workflow_receipt_mapper_gate as gate  # noqa: E402

EXAMPLES = WORKSPACE / "docs/workflow_intakes/examples"


def _intake(name: str = "support_refund_review.json") -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def mapped(tmp_path_factory):
    out = tmp_path_factory.mktemp("wrm") / "support_refund_review"
    m = M.map_workflow(_intake(), out)
    return {"out": out, "map": m}


@pytest.fixture(scope="module")
def suite(tmp_path_factory):
    root = tmp_path_factory.mktemp("suite") / "bundle"
    root.mkdir()
    for name in ["support_refund_review.json", "github_issue_triage.json",
                 "vendor_invoice_review.json"]:
        intake = _intake(name)
        M.map_workflow(intake, root / intake["workflow_id"])
    (root / "mapper_config.json").write_text(json.dumps(
        {"mapper": "hg_runtime.workflow_receipt_mapper", "synthetic_only": True}),
        encoding="utf-8")
    (root / "workflow_results.json").write_text(json.dumps(
        [d.name for d in root.iterdir() if d.is_dir()]), encoding="utf-8")
    (root / "proof_index.json").write_text(json.dumps({"workflows": 3}), encoding="utf-8")
    (root / "summary_report.md").write_text(
        "# Suite\nReceipt maps are governance artifacts; they do not deploy or certify.\n",
        encoding="utf-8")
    (root / "claim_boundary_report.md").write_text(
        "Maps the path. No customer deployment, no certification, no model correctness, "
        "no production operator auth. Synthetic examples; no external effects.\n",
        encoding="utf-8")
    # seal suite
    import hashlib
    files = sorted(p for p in root.rglob("*") if p.is_file()
                   and not (p.parent == root and p.name in {"checksums.sha256", "manifest.json"}))
    (root / "checksums.sha256").write_text(
        "\n".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(root).as_posix()}"
                  for p in files) + "\n", encoding="utf-8")
    (root / "manifest.json").write_text(json.dumps({"bundle": "wrm_suite"}), encoding="utf-8")
    return root


# 1. Good intake validates
def test_intake_validates():
    for n in ["support_refund_review.json", "github_issue_triage.json",
              "vendor_invoice_review.json"]:
        assert validate_intake(_intake(n)) == [], n


# 2. Missing required fields rejected
def test_intake_rejects_missing():
    bad = _intake()
    del bad["must_refuse_conditions"]
    assert any("must_refuse_conditions" in e for e in validate_intake(bad))


# 3. Redaction/safety rejects obvious secrets
def test_secret_scan_blocks():
    bad = _intake()
    bad["description"] += " api_key=sk-abcdefghijklmnopqrstuvwx1234"
    assert scan_for_secrets(bad)
    with pytest.raises(IntakeError):
        load_intake(bad)


# 4-7. Mapper produces required artifacts
def test_mapper_outputs(mapped):
    for f in ["receipt_map.json", "authority_boundary_map.json", "refusal_plan.json",
              "proof_bundle_plan.json", "receipt_plan.json", "runner_projection.json",
              "intake_redacted.json", "summary_report.md", "claim_boundary_report.md",
              "checksums.sha256"]:
        assert (mapped["out"] / f).is_file(), f


# 8. Scenario draft is draft-only
def test_scenario_draft_only(mapped):
    proj = json.loads((mapped["out"] / "runner_projection.json").read_text(encoding="utf-8"))
    assert proj["status"] == "DRAFT_ONLY_NOT_RUN"
    draft = json.loads((mapped["out"] / "scenario_config_draft.json").read_text(encoding="utf-8"))
    assert "DRAFT" in draft["title"]
    assert draft["mode"] == "fixture"


# 9. Manual-review-only workflows are honest (no draft, internal-only)
def test_manual_review_only_honest(tmp_path):
    m = M.map_workflow(_intake("vendor_invoice_review.json"), tmp_path / "v")
    assert m["runner_projection"]["status"] == "NOT_PROJECTABLE"
    assert not (tmp_path / "v" / "scenario_config_draft.json").exists()
    assert m["publicability"]["status"] in ("internal_only", "not_demoable")


# 10. Mapper performs no external effects (no network access in module)
def test_no_external_effects():
    import hg_runtime.workflow_receipt_mapper.mapper as mod
    import hg_runtime.workflow_receipt_mapper.schema as sch
    for module in (mod, sch):
        src = Path(module.__file__).read_text(encoding="utf-8")
        for marker in ("urllib.request", "requests.", "socket.", "http.client", "subprocess"):
            assert marker not in src, f"{module.__name__} must not touch {marker}"


# 11. Gate fails on missing receipt_map.json
def test_gate_missing_receipt_map(suite, tmp_path):
    b = tmp_path / "b"
    shutil.copytree(suite, b)
    (b / "support_refund_review" / "receipt_map.json").unlink()
    r = gate.run_gate(b, write_result=tmp_path / "g.json")
    assert r["verdict"].startswith("RED")


# 12. Gate fails on secret marker
def test_gate_secret_marker(suite, tmp_path):
    b = tmp_path / "b"
    shutil.copytree(suite, b)
    (b / "github_issue_triage" / "note.md").write_text(
        "leaked password: bearer AAAAAAAAAAAAAAAAAAAAAAAA", encoding="utf-8")
    r = gate.run_gate(b, write_result=tmp_path / "g.json")
    assert r["verdict"].startswith("RED")
    assert r["synthetic_data_only"] is False


# 13. Gate fails on production deployment claim
def test_gate_deployment_claim(suite, tmp_path):
    b = tmp_path / "b"
    shutil.copytree(suite, b)
    p = b / "summary_report.md"
    p.write_text(p.read_text(encoding="utf-8") +
                 "\nThis workflow is a live customer deployment today.\n", encoding="utf-8")
    _reseal(b)
    r = gate.run_gate(b, write_result=tmp_path / "g.json")
    assert r["claim_boundary_ok"] is False


# 14. Gate fails on model correctness claim
def test_gate_correctness_claim(suite, tmp_path):
    b = tmp_path / "b"
    shutil.copytree(suite, b)
    p = b / "summary_report.md"
    p.write_text(p.read_text(encoding="utf-8") +
                 "\nThe map proves model correctness in production.\n", encoding="utf-8")
    _reseal(b)
    r = gate.run_gate(b, write_result=tmp_path / "g.json")
    assert r["verdict"].startswith("RED")


# 15. Gate validates all three sample workflows
def test_gate_green_on_suite(suite, tmp_path):
    r = gate.run_gate(suite, write_result=tmp_path / "g.json")
    assert r["verdict"] == "GREEN_WORKFLOW_RECEIPT_MAPPER", r["verdict"]
    assert r["workflows_total"] == 3 and r["workflows_passed"] == 3


# 16. Checksums fail after tamper
def test_checksum_tamper(suite, tmp_path):
    b = tmp_path / "b"
    shutil.copytree(suite, b)
    p = b / "support_refund_review" / "summary_report.md"
    p.write_text(p.read_text(encoding="utf-8") + "\ntampered\n", encoding="utf-8")
    r = gate.run_gate(b, write_result=tmp_path / "g.json")
    assert r["verdict"].startswith("RED")
    assert any(not c["ok"] and "checksums" in c["name"] for c in r["checks"])


# 17. Publicability classification is honest
def test_publicability_honest(mapped):
    assert mapped["map"]["publicability"]["status"] == "internal_only"
    nonsynth = _intake()
    nonsynth["data_sensitivity"] = "confidential"
    nonsynth["synthetic_data"] = True  # sanitized flag
    assert M.build_publicability(nonsynth)["status"] == "needs_redaction"


# 18. Claim boundary report includes shows / does-not-show
def test_claim_boundary_sections(mapped):
    cb = mapped["map"]["claim_boundary"]
    assert cb["shows"] and cb["does_not_show"]
    text = (mapped["out"] / "claim_boundary_report.md").read_text(encoding="utf-8")
    assert "What this map shows" in text and "does not show" in text


def _reseal(root: Path) -> None:
    import hashlib
    files = sorted(p for p in root.rglob("*") if p.is_file()
                   and not (p.parent == root and p.name in {"checksums.sha256", "manifest.json"}))
    (root / "checksums.sha256").write_text(
        "\n".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(root).as_posix()}"
                  for p in files) + "\n", encoding="utf-8")
