"""Pack4: Process audit gating unit tests (Layer 9). Real get_process_audit with temp dir; no mocks."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from hg_core.stakes.gating import check_gate, GateResult


def _audit_artifacts_root(workspace_root: Path) -> Path:
    return workspace_root / "artifacts" / "alignment_science" / "process_audit"


def _safe_decision_id(decision_id: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in decision_id)[:64]


def _write_audit(workspace_root: Path, decision_id: str, process_compliance_score: float, legible: bool, date_dir: str = "2026-03-04") -> None:
    root = _audit_artifacts_root(workspace_root) / date_dir
    root.mkdir(parents=True, exist_ok=True)
    safe_id = _safe_decision_id(decision_id)
    path = root / f"{safe_id}.json"
    data = {
        "decision_id": decision_id,
        "process_compliance_score": process_compliance_score,
        "legible": legible,
        "artifact_ref": str(path),
        "created_at": "2026-03-04T12:00:00Z",
    }
    path.write_text(json.dumps(data), encoding="utf-8")


def test_gate_allow_when_legible_and_score_above_min(tmp_path: Path) -> None:
    """When policy has process_legible_required and process_score_min, valid audit -> allow."""
    _write_audit(tmp_path, "dec-allow", process_compliance_score=0.8, legible=True)
    policy = {"process_legible_required": True, "process_score_min": 0.5, "budget": {"default_limit": 100}, "action_costs": {"READ": 0.1}}
    r = check_gate(
        "READ", "agent1", current_budget_used=0, trust_band=2, escrow_locked=0,
        policy=policy, workspace_root=tmp_path, decision_id="dec-allow",
    )
    assert r.allowed is True
    assert r.reason == "ok"


def test_gate_deny_process_not_legible(tmp_path: Path) -> None:
    """When process_legible_required and audit has legible=false -> deny process_not_legible."""
    _write_audit(tmp_path, "dec-not-legible", process_compliance_score=0.3, legible=False)
    policy = {"process_legible_required": True, "budget": {"default_limit": 100}, "action_costs": {"READ": 0.1}}
    r = check_gate(
        "READ", "agent1", current_budget_used=0, trust_band=2, escrow_locked=0,
        policy=policy, workspace_root=tmp_path, decision_id="dec-not-legible",
    )
    assert r.allowed is False
    assert r.reason == "process_not_legible"


def test_gate_deny_process_score_below_min(tmp_path: Path) -> None:
    """When process_score_min set and score below min -> deny process_score_below_min."""
    _write_audit(tmp_path, "dec-low-score", process_compliance_score=0.3, legible=True)
    policy = {"process_score_min": 0.5, "budget": {"default_limit": 100}, "action_costs": {"READ": 0.1}}
    r = check_gate(
        "READ", "agent1", current_budget_used=0, trust_band=2, escrow_locked=0,
        policy=policy, workspace_root=tmp_path, decision_id="dec-low-score",
    )
    assert r.allowed is False
    assert r.reason == "process_score_below_min"


def test_gate_deny_process_audit_missing(tmp_path: Path) -> None:
    """When decision_id given but no audit artifact -> deny process_audit_missing."""
    # No file written for "dec-missing"
    policy = {"process_legible_required": True, "budget": {"default_limit": 100}, "action_costs": {"READ": 0.1}}
    r = check_gate(
        "READ", "agent1", current_budget_used=0, trust_band=2, escrow_locked=0,
        policy=policy, workspace_root=tmp_path, decision_id="dec-missing",
    )
    assert r.allowed is False
    assert r.reason == "process_audit_missing"


def test_gate_deny_process_audit_check_failed(tmp_path: Path) -> None:
    """When get_process_audit raises (e.g. audit root is a file not dir) -> deny process_audit_check_failed."""
    # Make artifacts/alignment_science/process_audit a file so root.iterdir() raises NotADirectoryError.
    audit_root = _audit_artifacts_root(tmp_path)
    audit_root.parent.mkdir(parents=True, exist_ok=True)
    audit_root.write_text("x")
    policy = {"process_legible_required": True, "budget": {"default_limit": 100}, "action_costs": {"READ": 0.1}}
    r = check_gate(
        "READ", "agent1", current_budget_used=0, trust_band=2, escrow_locked=0,
        policy=policy, workspace_root=tmp_path, decision_id="dec-any",
    )
    assert r.allowed is False
    assert r.reason == "process_audit_check_failed"


def test_gate_no_process_requirement_ignores_decision_id(tmp_path: Path) -> None:
    """When policy has no process_legible_required or process_score_min, decision_id/audit not checked."""
    policy = {"budget": {"default_limit": 100}, "action_costs": {"READ": 0.1}}
    r = check_gate(
        "READ", "agent1", current_budget_used=0, trust_band=2, escrow_locked=0,
        policy=policy, workspace_root=tmp_path, decision_id="dec-missing",
    )
    assert r.allowed is True
    assert r.reason == "ok"


def test_gating_integration_structured_denial_and_reason(tmp_path: Path) -> None:
    """Integration: policy from disk, no audit for decision_id -> structured denial (process_audit_missing)."""
    from hg_core.stakes import load_policy

    policy_dir = tmp_path / "artifacts" / "policy"
    policy_dir.mkdir(parents=True, exist_ok=True)
    (policy_dir / "trust_and_budget_policy.yaml").write_text(
        "process_legible_required: true\nbudget: { default_limit: 100 }\naction_costs: { READ: 0.1 }\n",
        encoding="utf-8",
    )
    policy = load_policy(tmp_path)
    assert policy.get("process_legible_required") is True
    r = check_gate(
        "READ", "agent1", current_budget_used=0, trust_band=2, escrow_locked=0,
        policy=policy, workspace_root=tmp_path, decision_id="integration-dec-missing",
    )
    assert r.allowed is False
    assert r.reason == "process_audit_missing"
    assert r.approval_required is True
