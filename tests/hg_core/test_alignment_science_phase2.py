"""
Layer 9 Phase 2: Process-oriented evaluation pipeline tests.
Process score computed, gating requires legible process, artifact stored.
"""
from pathlib import Path

import pytest

from hg_core.alignment_science import (
    run_process_audit,
    get_process_audit,
    get_process_audit_api,
    run_process_audit_api,
)
from hg_core.alignment_science.process_audit import _compute_score_and_legible
from hg_core.stakes import check_gate, GateResult


def test_compute_score_and_legible_rich_path() -> None:
    proof = {
        "decision": {"based_on_claim_ids": ["c1"], "value_weights": [], "title": "T", "event_id": "e1"},
        "predictions": [{}],
        "evaluations": [{}],
        "representation_inspection_result": [{}],
    }
    score, legible = _compute_score_and_legible(proof)
    assert 0 <= score <= 1
    assert legible is True


def test_compute_score_and_legible_empty_path() -> None:
    proof = {"decision": {}, "predictions": [], "evaluations": []}
    score, legible = _compute_score_and_legible(proof)
    assert score >= 0
    assert legible is False


def test_run_process_audit_produces_score_and_artifact(tmp_path: Path) -> None:
    result = run_process_audit(tmp_path, "dec-1", emit_ledger=False)
    assert "process_compliance_score" in result
    assert 0 <= result["process_compliance_score"] <= 1
    assert "legible" in result
    assert "artifact_ref" in result
    artifact_path = Path(result["artifact_ref"])
    assert artifact_path.exists()
    assert result["decision_id"] == "dec-1"


def test_get_process_audit_returns_none_when_missing(tmp_path: Path) -> None:
    assert get_process_audit(tmp_path, "nonexistent-decision") is None


def test_get_process_audit_returns_result_after_run(tmp_path: Path) -> None:
    run_process_audit(tmp_path, "dec-2", emit_ledger=False)
    out = get_process_audit(tmp_path, "dec-2")
    assert out is not None
    assert out["decision_id"] == "dec-2"
    assert "process_compliance_score" in out


def test_gating_allows_when_no_process_policy(tmp_path: Path) -> None:
    policy = {"trust_bands": [{"max_action": "WRITE"}], "budget": {"default_limit": 100.0}}
    r = check_gate("WRITE", "agent1", 0.0, 0, 0.0, policy, tmp_path, decision_id="any")
    assert r.allowed is True


def test_gating_denies_when_process_legible_required_and_no_audit(tmp_path: Path) -> None:
    policy = {"process_legible_required": True}
    r = check_gate("WRITE", "agent1", 0.0, 0, 0.0, policy, tmp_path, decision_id="dec-no-audit")
    assert r.allowed is False
    assert "process" in r.reason.lower()


def test_gating_denies_when_process_legible_required_and_audit_not_legible(tmp_path: Path) -> None:
    run_process_audit(tmp_path, "dec-low", emit_ledger=False)
    audit = get_process_audit(tmp_path, "dec-low")
    if audit and audit.get("legible"):
        pytest.skip("audit happened to be legible in this env")
    policy = {"process_legible_required": True}
    r = check_gate("WRITE", "agent1", 0.0, 0, 0.0, policy, tmp_path, decision_id="dec-low")
    if audit is None:
        assert r.allowed is False
    else:
        assert r.allowed is False or audit.get("legible") is True


def test_gating_allows_when_process_legible_required_and_audit_legible(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """When policy requires legible and get_process_audit returns legible=True, gate allows."""
    from hg_core.alignment_science import process_audit as pa_mod
    legible_audit = {"decision_id": "dec-legible", "process_compliance_score": 0.9, "legible": True, "artifact_ref": ""}
    def fake_get(_root: Path, decision_id: str):
        return legible_audit if decision_id == "dec-legible" else None
    monkeypatch.setattr(pa_mod, "get_process_audit", fake_get)
    policy = {"process_legible_required": True}
    r = check_gate("WRITE", "agent1", 0.0, 0, 0.0, policy, tmp_path, decision_id="dec-legible")
    assert r.allowed is True


def test_process_score_min_denies_when_below(tmp_path: Path) -> None:
    run_process_audit(tmp_path, "dec-4", emit_ledger=False)
    policy = {"process_score_min": 1.0}
    r = check_gate("WRITE", "agent1", 0.0, 0, 0.0, policy, tmp_path, decision_id="dec-4")
    assert r.allowed is False
    assert "score" in r.reason.lower() or "process" in r.reason.lower()


def test_get_process_audit_api_decision_id(tmp_path: Path) -> None:
    run_process_audit(tmp_path, "dec-api", emit_ledger=False)
    out = get_process_audit_api(tmp_path, decision_id="dec-api")
    assert out["ok"] is True
    assert "result" in out
    assert out["result"]["decision_id"] == "dec-api"


def test_get_process_audit_api_not_found(tmp_path: Path) -> None:
    out = get_process_audit_api(tmp_path, decision_id="no-such")
    assert out["ok"] is False
    assert out.get("error") == "not_found"


def test_run_process_audit_api_returns_result(tmp_path: Path) -> None:
    out = run_process_audit_api(tmp_path, "dec-post", emit_ledger=False)
    assert out["ok"] is True
    assert "result" in out
    assert out["result"]["decision_id"] == "dec-post"
