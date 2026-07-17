"""Reusable GRS demo runner tests — the 20 required cases.

Run: python -m pytest --import-mode=importlib -q tests/grs_demo_runner
Assertions read JSON verdicts and bundle files, never exit codes.
Live-model behavior is tested against an unreachable endpoint (fail-closed);
no test fakes a live call.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
OUTER = WORKSPACE.parent
sys.path.insert(0, str(WORKSPACE))
sys.path.insert(0, str(WORKSPACE / "scripts" / "evals"))

from hg_runtime.demos.grs_runner import runner as R  # noqa: E402
from hg_runtime.demos.grs_runner.scenario_schema import (  # noqa: E402
    ScenarioError, publicability, validate_scenario,
)
from hg_runtime.demos.grs_runner.suite import run_suite, seal_suite  # noqa: E402
import grs_demo_runner_gate as gate  # noqa: E402

SCENARIO_DIR = WORKSPACE / "docs/demo_scenarios/grs"
CANONICAL = WORKSPACE / "docs/proofs/governed_research_soak/operator_ui_live"


def _load(name: str) -> dict:
    return json.loads((SCENARIO_DIR / name).read_text(encoding="utf-8"))


def _fixture_scenario(sid: str = "agent_workflow_policy_fixture") -> dict:
    s = _load("agent_workflow_policy_fixture.json")
    s["scenario_id"] = sid
    return s


@pytest.fixture(scope="module")
def fixture_run(tmp_path_factory):
    out = tmp_path_factory.mktemp("run") / "s"
    index = R.run_scenario(_fixture_scenario(), out)
    return {"out": out, "index": index}


@pytest.fixture(scope="module")
def suite_bundle(tmp_path_factory):
    root = tmp_path_factory.mktemp("suite")
    cfg1 = root / "a.json"
    cfg2 = root / "b.json"
    cfg1.write_text(json.dumps(_fixture_scenario("scenario_a")), encoding="utf-8")
    s2 = _fixture_scenario("scenario_b")
    s2["question"] = "How should refusal receipts be surfaced to an operator?"
    cfg2.write_text(json.dumps(s2), encoding="utf-8")
    result = run_suite([cfg1, cfg2], root / "bundles")
    out = Path(result["output_dir"])
    (out / "summary_report.md").write_text(
        "# Suite summary\nProof records the path. It does not prove model correctness.\n",
        encoding="utf-8")
    (out / "claim_boundary_report.md").write_text(
        "Source is receipt, not truth. Local signed demo operator is not production auth.\n",
        encoding="utf-8")
    seal_suite(out)
    return out


# 1. Schema validates good scenarios
def test_schema_validates_good_scenarios():
    assert validate_scenario(_load("local_inference_latency_live.json")) == []
    assert validate_scenario(_load("agent_workflow_policy_fixture.json")) == []


# 2. Schema rejects missing required fields
def test_schema_rejects_missing_fields():
    s = _fixture_scenario()
    del s["operator_review"]
    errors = validate_scenario(s)
    assert any("operator_review" in e for e in errors)


# 3. Live mode fails when endpoint unavailable and require_live_model
def test_live_mode_fails_when_endpoint_down(tmp_path):
    s = _load("local_inference_latency_live.json")
    s["model"]["endpoint"] = "http://127.0.0.1:59999/v1"  # nothing listens here
    with pytest.raises(R.LiveModeUnavailable):
        R.run_scenario(s, tmp_path / "s")


# 4. Fixture fallback is rejected in live mode (failure, not degradation)
def test_no_silent_fixture_fallback(tmp_path):
    s = _load("local_inference_latency_live.json")
    s["model"]["endpoint"] = "http://127.0.0.1:59999/v1"
    out = tmp_path / "s"
    with pytest.raises(R.LiveModeUnavailable):
        R.run_scenario(s, out)
    assert not (out / "model_proposal_receipt.json").exists()
    assert not (out / "fixture_label.json").exists()


# 5. Fixture mode is labelled and cannot be public
def test_fixture_labelled_and_internal_only(fixture_run):
    assert (fixture_run["out"] / "fixture_label.json").is_file()
    assert fixture_run["index"]["publicability"] == "INTERNAL_ONLY"
    assert publicability(_fixture_scenario()) == "INTERNAL_ONLY"


# 6. Cloud providers disabled by default
def test_cloud_provider_disabled():
    s = _load("local_inference_latency_live.json")
    s["model"]["cloud_providers_allowed"] = True
    errors = validate_scenario(s)
    assert any("cloud" in e for e in errors)


# 7. Live source mode requires allowlist
def test_live_sources_require_allowlist():
    s = _load("local_inference_latency_live.json")
    s["sources"]["allowlist"] = []
    errors = validate_scenario(s)
    assert any("allowlist" in e for e in errors)


# 8. Runner writes required proof bundle files
def test_runner_writes_required_files(fixture_run):
    for f in gate.SCENARIO_REQUIRED:
        assert (fixture_run["out"] / f).is_file(), f


# 9/10. Approve and deny present when configured
def test_approve_and_deny_present(fixture_run):
    lines = (fixture_run["out"] / "operator_decision_receipts.jsonl").read_text(
        encoding="utf-8").splitlines()
    decisions = [json.loads(l) for l in lines]
    assert any(d["decision"] == "approve" for d in decisions)
    assert any(d["decision"] == "deny" for d in decisions)
    assert all(d["production_operator_auth"] is False for d in decisions)


# 11/12. Promotion requires approve; denied never promoted
def test_promotion_discipline(fixture_run):
    promo = json.loads((fixture_run["out"] / "promotion_receipt.json").read_text(encoding="utf-8"))
    decisions = [json.loads(l) for l in
                 (fixture_run["out"] / "operator_decision_receipts.jsonl").read_text(
                     encoding="utf-8").splitlines()]
    approved = {d["claim_id"] for d in decisions if d["decision"] == "approve"}
    denied = {d["claim_id"] for d in decisions if d["decision"] == "deny"}
    assert set(promo["promoted_claims"]) <= approved
    assert not set(promo["promoted_claims"]) & denied
    assert denied <= set(promo["denied_claims_not_promoted"])


# 13. Final document references receipt/source ids
def test_final_document_references(fixture_run):
    doc = (fixture_run["out"] / "final_document.md").read_text(encoding="utf-8")
    assert "decision receipt" in doc
    assert "sha256:" in doc
    assert "does not prove model correctness" in doc


# 14. Claim boundary blocks model-correctness wording
def test_claim_firewall_blocks_correctness(suite_bundle, tmp_path):
    b = tmp_path / "bundle"
    shutil.copytree(suite_bundle, b)
    p = b / "summary_report.md"
    p.write_text(p.read_text(encoding="utf-8") +
                 "\nThis run proves model correctness beyond doubt.\n", encoding="utf-8")
    seal_suite(b)
    r = gate.run_gate(b, write_result=tmp_path / "g.json")
    assert r["claim_boundary_ok"] is False
    assert r["verdict"].startswith("RED")


# 15. Gate fails on missing scenario config
def test_gate_fails_missing_scenario_config(suite_bundle, tmp_path):
    b = tmp_path / "bundle"
    shutil.copytree(suite_bundle, b)
    (b / "scenario_1" / "scenario_config.json").unlink()
    r = gate.run_gate(b, write_result=tmp_path / "g.json")
    assert r["verdict"].startswith("RED")


# 16. Gate fails on tampered checksum
def test_gate_fails_tampered_checksum(suite_bundle, tmp_path):
    b = tmp_path / "bundle"
    shutil.copytree(suite_bundle, b)
    p = b / "scenario_1" / "final_document.md"
    p.write_text(p.read_text(encoding="utf-8") + "\ntampered\n", encoding="utf-8")
    r = gate.run_gate(b, write_result=tmp_path / "g.json")
    assert r["verdict"].startswith("RED")
    assert any(not c["ok"] and "checksums" in c["name"] for c in r["checks"])


# 17. Gate writes gate_result.json (fixture-only suite = honest YELLOW)
def test_gate_writes_result(suite_bundle, tmp_path):
    r = gate.run_gate(suite_bundle, write_result=tmp_path / "g.json")
    assert (tmp_path / "g.json").is_file()
    assert r["verdict"].startswith("YELLOW"), r["verdict"]
    assert r["fixture_used"] is True


# 18. Second scenario runs through the same runner architecture
def test_second_scenario_same_architecture(suite_bundle):
    idx1 = json.loads((suite_bundle / "scenario_1" / "proof_index.json").read_text(encoding="utf-8"))
    idx2 = json.loads((suite_bundle / "scenario_2" / "proof_index.json").read_text(encoding="utf-8"))
    assert idx1["proof_type"] == idx2["proof_type"] == "grs_runner_scenario"
    assert idx1["scenario_id"] != idx2["scenario_id"]


# 19. Canonical GRS public proof bundle is not mutated by runs
def test_canonical_bundle_not_mutated(fixture_run):
    out = subprocess.run(["git", "status", "--porcelain", "--",
                          "docs/proofs/governed_research_soak"],
                         cwd=WORKSPACE, capture_output=True, text=True, timeout=120).stdout
    assert out.strip() == "", out


# 20. V3 site path is not mutated
def test_v3_not_mutated():
    out = subprocess.run(["git", "status", "--porcelain", "--", "docs/marketing"],
                         cwd=OUTER, capture_output=True, text=True, timeout=120).stdout
    assert out.strip() == "", out
