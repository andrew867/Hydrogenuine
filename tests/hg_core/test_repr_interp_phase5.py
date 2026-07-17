"""
Tests for Layer 8 Phase 5: Refusal-inspection and backward-patching under governance.
"""
from pathlib import Path

import pytest

from hg_core.repr_interp import (
    is_refusal_inspection_enabled,
    record_refusal_inspection,
    get_inspection_results,
    propose_patch,
    apply_patch,
    allow_patch_under_governance,
    get_patch,
    list_patch_proposals,
    patch_proposal,
    patch_record,
    PATCH_STATUS_PROPOSED,
    PATCH_STATUS_APPLIED,
)


def test_refusal_inspection_disabled_by_default() -> None:
    assert is_refusal_inspection_enabled() is False


def test_refusal_inspection_enabled_via_run_config() -> None:
    assert is_refusal_inspection_enabled(run_config={"repr_interp_refusal_inspection": True}) is True


def test_record_refusal_inspection_stores_result(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    out = record_refusal_inspection(
        tmp_path,
        "budget_exceeded",
        event_id="ev-1",
        run_id="run-1",
        node_id="node-1",
        run_dir=run_dir,
    )
    assert out is not None
    assert out["prompt_id"] == "refusal_reason"
    assert out["output_text"] == "budget_exceeded"
    results = get_inspection_results(tmp_path, run_dir=run_dir)
    assert len(results) >= 1
    assert any(r.get("node_id") == "node-1" for r in results)


def test_record_refusal_inspection_with_decision_id_writes_global(tmp_path: Path) -> None:
    record_refusal_inspection(tmp_path, "policy_denied", decision_id="dec-1")
    results = get_inspection_results(tmp_path, decision_id="dec-1")
    assert len(results) == 1
    assert results[0]["decision_id"] == "dec-1"


def test_patch_proposal_schema() -> None:
    p = patch_proposal("dec-1", "override_refusal", "Allowed output", "Operator override", "op-1")
    assert p["decision_id"] == "dec-1"
    assert p["patch_type"] == "override_refusal"
    assert p["proposed_output"] == "Allowed output"


def test_patch_record_schema() -> None:
    r = patch_record("pid-1", "dec-1", "override", "out", "rationale", "op", status=PATCH_STATUS_PROPOSED)
    assert r["patch_id"] == "pid-1"
    assert r["status"] == PATCH_STATUS_PROPOSED


def test_propose_patch_creates_record(tmp_path: Path) -> None:
    rec = propose_patch(tmp_path, "dec-1", "override_refusal", "New output", "Rationale", "op-1")
    assert "patch_id" in rec
    assert rec["decision_id"] == "dec-1"
    assert rec["status"] == PATCH_STATUS_PROPOSED
    proposals = list_patch_proposals(tmp_path, decision_id="dec-1")
    assert len(proposals) == 1
    assert proposals[0]["patch_id"] == rec["patch_id"]


def test_get_patch_returns_proposal(tmp_path: Path) -> None:
    rec = propose_patch(tmp_path, "dec-2", "type", "out", "rationale")
    patch_id = rec["patch_id"]
    loaded = get_patch(tmp_path, patch_id)
    assert loaded is not None
    assert loaded["patch_id"] == patch_id


def test_allow_patch_under_governance_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("HG_ALLOW_BACKWARD_PATCH", raising=False)
    assert allow_patch_under_governance(tmp_path, "patch-1") is False
    monkeypatch.setenv("HG_ALLOW_BACKWARD_PATCH", "1")
    assert allow_patch_under_governance(tmp_path, "patch-1") is True


def test_allow_patch_under_governance_policy(tmp_path: Path) -> None:
    assert allow_patch_under_governance(tmp_path, "any", policy={"allow_backward_patch": True}) is True
    assert allow_patch_under_governance(tmp_path, "any", policy={}) is False


def test_apply_patch_requires_governance(tmp_path: Path) -> None:
    rec = propose_patch(tmp_path, "dec-3", "type", "out", "rationale")
    patch_id = rec["patch_id"]
    result = apply_patch(tmp_path, patch_id)
    assert result.get("ok") is False
    assert "governance" in (result.get("error") or "").lower() or "disallows" in (result.get("error") or "").lower()


def test_apply_patch_when_allowed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HG_ALLOW_BACKWARD_PATCH", "1")
    rec = propose_patch(tmp_path, "dec-4", "type", "out", "rationale")
    patch_id = rec["patch_id"]
    result = apply_patch(tmp_path, patch_id, policy={"allow_backward_patch": True})
    assert result.get("ok") is True
    assert "applied_at" in result
    # get_patch reads applied record from artifacts/repr_interp/patches/applied/<patch_id>.json
    loaded = get_patch(tmp_path, patch_id)
    assert loaded is not None
    assert loaded["status"] == PATCH_STATUS_APPLIED
