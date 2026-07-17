"""P29-0 tool workbench schema tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_runtime.tool_mediated_workbench.fixtures import build_p29_0_layer, replay_p29_0
from hg_runtime.tool_mediated_workbench.redaction import secret_scan
from hg_runtime.tool_mediated_workbench.schemas import (
    FORBIDDEN_TRUE,
    P29_INVARIANTS,
    RECORD_TYPES,
    REFUSAL_REASONS,
    SANDBOX_RESULT_STATES,
    TOOL_REQUEST_TYPES,
    ToolWorkbenchBoundaryError,
    neutral_flags,
)
from hg_runtime.tool_mediated_workbench.tool_plan import build_tool_plan
from hg_runtime.tool_mediated_workbench.tool_request import build_tool_request
from hg_runtime.tool_mediated_workbench.tool_sandbox import build_sandbox_result
from hg_runtime.tool_mediated_workbench.tool_workbench_policy import build_tool_workbench_policy
from hg_runtime.tool_mediated_workbench.workbench_gate import validate_p29_0_gate

ROOT = Path(__file__).resolve().parents[2]


# --- Schema constants -------------------------------------------------------

def test_record_types_present():
    assert len(RECORD_TYPES) == 7


def test_invariants_present():
    assert len(P29_INVARIANTS) == 13


def test_request_types_present():
    assert len(TOOL_REQUEST_TYPES) >= 7


def test_sandbox_result_states_present():
    assert len(SANDBOX_RESULT_STATES) == 3


def test_refusal_reasons_present():
    assert len(REFUSAL_REASONS) == 8


def test_neutral_flags_all_false():
    for k, v in neutral_flags().items():
        assert v is False, f"{k} is not False"


def test_forbidden_true_matches_neutral():
    assert FORBIDDEN_TRUE == set(neutral_flags())


# --- Policy ------------------------------------------------------------------

def test_policy_builder():
    p = build_tool_workbench_policy()
    assert p["record_type"] == "tool_workbench_policy_v1"
    assert p["live_tool_execution_enabled"] is False
    assert p["sandbox_only"] is True
    assert p["dry_run_only"] is True
    assert p["operator_approval_required"] is True
    assert p["tool_plan_is_not_permission"] is True
    assert p["tool_request_is_not_execution"] is True
    assert p["sandbox_result_is_not_live_result"] is True
    assert p["domain_pack_does_not_grant_tools"] is True
    assert "policy_hash" in p


# --- Request -----------------------------------------------------------------

def test_request_builder():
    r = build_tool_request(
        request_id="r1", request_type="local_read",
        tool_name="read", description="test",
    )
    assert r["record_type"] == "tool_request_v1"
    assert r["tool_request_is_not_execution"] is True
    assert "request_hash" in r


def test_request_rejects_unknown_type():
    with pytest.raises(ToolWorkbenchBoundaryError):
        build_tool_request(
            request_id="r1", request_type="UNKNOWN",
            tool_name="x", description="x",
        )


# --- Plan --------------------------------------------------------------------

def test_plan_builder():
    req = build_tool_request(
        request_id="r1", request_type="local_read",
        tool_name="read", description="test",
    )
    p = build_tool_plan(
        plan_id="p1", domain_pack_id="pack-1",
        skill_ids=["s1"], tool_requests=[req],
        provenance_refs=["ref1"],
    )
    assert p["record_type"] == "tool_plan_v1"
    assert p["tool_plan_is_not_permission"] is True
    assert p["domain_pack_does_not_grant_tools"] is True
    assert "plan_hash" in p


# --- Sandbox -----------------------------------------------------------------

def test_sandbox_builder():
    s = build_sandbox_result(
        sandbox_id="s1", request_id="r1", plan_id="p1",
        result_state="DRY_RUN_COMPLETE",
    )
    assert s["record_type"] == "tool_sandbox_result_v1"
    assert s["sandbox_result_is_not_live_result"] is True
    assert s["dry_run_is_not_live_effect"] is True
    assert "sandbox_hash" in s


def test_sandbox_rejects_unknown_state():
    with pytest.raises(ToolWorkbenchBoundaryError):
        build_sandbox_result(
            sandbox_id="s1", request_id="r1", plan_id="p1",
            result_state="UNKNOWN",
        )


# --- Fixture layer -----------------------------------------------------------

def test_p29_0_layer_builds():
    layer = build_p29_0_layer(ROOT)
    assert layer["policy"]
    assert len(layer["requests"]) >= 2
    assert len(layer["plans"]) >= 1
    assert len(layer["sandbox_results"]) >= 2
    assert len(layer["receipts"]) >= 1
    assert "manifest_hash" in layer["manifest"]


def test_p29_0_layer_neutral_flags():
    layer = build_p29_0_layer(ROOT)
    for record in [layer["policy"]] + layer["requests"] + layer["plans"] + layer["sandbox_results"] + layer["receipts"]:
        for flag in FORBIDDEN_TRUE:
            assert record.get(flag, False) is False, f"{flag} is True in {record.get('record_type')}"


# --- Replay ------------------------------------------------------------------

def test_replay_deterministic():
    layer = build_p29_0_layer(ROOT)
    replay = replay_p29_0(ROOT, layer["manifest"]["manifest_hash"])
    assert replay["replay_preserves_manifest_hash"] is True


def test_replay_detects_mutation():
    replay = replay_p29_0(ROOT, "mutated_hash")
    assert replay["replay_preserves_manifest_hash"] is False


# --- Redaction ---------------------------------------------------------------

def test_secret_scan_passes():
    layer = build_p29_0_layer(ROOT)
    assert secret_scan(layer) is True


# --- Gate --------------------------------------------------------------------

def _summary(**overrides):
    data = {
        "policy_written": True,
        "request_written": True,
        "plan_written": True,
        "sandbox_written": True,
        "receipt_written": True,
        "tool_plan_not_permission": True,
        "tool_request_not_execution": True,
        "sandbox_not_live": True,
        "dry_run_not_live": True,
        "receipt_not_authority": True,
        "domain_pack_no_tools": True,
        "no_tool_authorization": True,
        "no_live_effects": True,
        "no_web_provider": True,
        "no_patch_application": True,
        "no_deletion": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_deterministic": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_gate_passes_full_summary():
    assert validate_p29_0_gate(_summary())["ok"] is True


def test_gate_refuses_missing_policy():
    assert validate_p29_0_gate(_summary(policy_written=False))["ok"] is False


def test_gate_refuses_tool_authorization():
    assert validate_p29_0_gate(_summary(tool_authorization_granted=True))["ok"] is False


def test_gate_refuses_live_execution():
    assert validate_p29_0_gate(_summary(tool_request_executed_live=True))["ok"] is False


def test_gate_refuses_plan_as_permission():
    assert validate_p29_0_gate(_summary(tool_plan_treated_as_permission=True))["ok"] is False


def test_gate_refuses_patch():
    assert validate_p29_0_gate(_summary(patch_request_applied=True))["ok"] is False


def test_gate_refuses_deletion():
    assert validate_p29_0_gate(_summary(deletion_performed=True))["ok"] is False
