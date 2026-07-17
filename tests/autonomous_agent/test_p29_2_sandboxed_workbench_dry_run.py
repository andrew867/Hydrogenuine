"""P29-2 sandboxed workbench dry run tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_runtime.tool_mediated_workbench.redaction import secret_scan
from hg_runtime.tool_mediated_workbench.schemas import (
    FORBIDDEN_TRUE,
    REFUSAL_REASONS,
    ToolWorkbenchBoundaryError,
)
from hg_runtime.tool_mediated_workbench.sandbox_simulator import simulate_tool_plan
from hg_runtime.tool_mediated_workbench.tool_refusal import build_refusal_record
from hg_runtime.tool_mediated_workbench.tool_request import build_tool_request
from hg_runtime.tool_mediated_workbench.workbench_dry_run import build_dry_run_layer, replay_dry_run
from hg_runtime.tool_mediated_workbench.workbench_gate import validate_p29_2_gate

ROOT = Path(__file__).resolve().parents[2]


# --- Refusal builder --------------------------------------------------------

def test_refusal_builder():
    r = build_refusal_record(
        refusal_id="r1", request_id="req1", plan_id="p1",
        refusal_reason="live_web_request",
    )
    assert r["record_type"] == "tool_refusal_record_v1"
    assert r["action_performed"] is False
    assert r["status"] == "REFUSED"
    assert "refusal_hash" in r


def test_refusal_rejects_unknown_reason():
    with pytest.raises(ToolWorkbenchBoundaryError):
        build_refusal_record(
            refusal_id="r1", request_id="req1", plan_id="p1",
            refusal_reason="UNKNOWN_REASON",
        )


# --- Simulator ---------------------------------------------------------------

def test_simulator_refuses_web_fetch():
    plan = {"plan_id": "p1", "tool_request_ids": ["r1"], "domain_pack_does_not_grant_tools": True}
    req = build_tool_request(request_id="r1", request_type="web_fetch", tool_name="web", description="web")
    sim = simulate_tool_plan(plan=plan, requests=[req], policy={})
    assert any(s["result_state"] == "REFUSED_BY_POLICY" for s in sim["sandbox_results"])
    assert any(r["refusal_reason"] == "live_web_request" for r in sim["refusals"])


def test_simulator_dry_runs_local_read():
    plan = {"plan_id": "p1", "tool_request_ids": ["r1"], "domain_pack_does_not_grant_tools": True}
    req = build_tool_request(request_id="r1", request_type="local_read", tool_name="read", description="read")
    sim = simulate_tool_plan(plan=plan, requests=[req], policy={})
    assert any(s["result_state"] == "DRY_RUN_COMPLETE" for s in sim["sandbox_results"])


def test_simulator_refuses_patch():
    plan = {"plan_id": "p1", "tool_request_ids": ["r1"], "domain_pack_does_not_grant_tools": True}
    req = build_tool_request(request_id="r1", request_type="patch_application", tool_name="patch", description="p")
    sim = simulate_tool_plan(plan=plan, requests=[req], policy={})
    assert any(r["refusal_reason"] == "patch_application_request" for r in sim["refusals"])


def test_simulator_refuses_deletion():
    plan = {"plan_id": "p1", "tool_request_ids": ["r1"], "domain_pack_does_not_grant_tools": True}
    req = build_tool_request(request_id="r1", request_type="deletion", tool_name="del", description="d")
    sim = simulate_tool_plan(plan=plan, requests=[req], policy={})
    assert any(r["refusal_reason"] == "deletion_request" for r in sim["refusals"])


# --- Dry run layer -----------------------------------------------------------

def test_dry_run_layer_builds():
    layer = build_dry_run_layer(ROOT)
    assert layer["sandbox_results"]
    assert layer["refusals"]
    assert layer["receipts"]


def test_dry_run_all_refusal_reasons_covered():
    layer = build_dry_run_layer(ROOT)
    covered = {r["refusal_reason"] for r in layer["refusals"]}
    assert REFUSAL_REASONS <= covered


def test_dry_run_no_live_execution():
    layer = build_dry_run_layer(ROOT)
    for s in layer["sandbox_results"]:
        assert s["sandbox_result_is_not_live_result"] is True


def test_dry_run_neutral_flags():
    layer = build_dry_run_layer(ROOT)
    for s in layer["sandbox_results"]:
        for flag in FORBIDDEN_TRUE:
            assert s.get(flag, False) is False
    for r in layer["refusals"]:
        for flag in FORBIDDEN_TRUE:
            assert r.get(flag, False) is False


# --- Replay ------------------------------------------------------------------

def test_replay_deterministic():
    layer = build_dry_run_layer(ROOT)
    replay = replay_dry_run(ROOT, layer["manifest"]["manifest_hash"])
    assert replay["replay_preserves_manifest_hash"] is True


def test_replay_detects_mutation():
    replay = replay_dry_run(ROOT, "mutated")
    assert replay["replay_preserves_manifest_hash"] is False


# --- Redaction ---------------------------------------------------------------

def test_secret_scan_passes():
    layer = build_dry_run_layer(ROOT)
    assert secret_scan(layer) is True


# --- Gate --------------------------------------------------------------------

def _summary(**overrides):
    data = {
        "p29_1_green": True,
        "sandbox_results_produced": True,
        "refusals_produced": True,
        "all_refusal_reasons_covered": True,
        "no_live_execution": True,
        "sandbox_not_live": True,
        "dry_run_not_live": True,
        "no_tool_authorization": True,
        "no_live_effects": True,
        "no_web_provider": True,
        "no_patch_application": True,
        "no_deletion": True,
        "no_belief_promotion": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_deterministic": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_gate_passes():
    assert validate_p29_2_gate(_summary())["ok"] is True


def test_gate_refuses_missing_p29_1():
    assert validate_p29_2_gate(_summary(p29_1_green=False))["ok"] is False


def test_gate_refuses_no_refusals():
    assert validate_p29_2_gate(_summary(refusals_produced=False))["ok"] is False


def test_gate_refuses_incomplete_refusal_reasons():
    assert validate_p29_2_gate(_summary(all_refusal_reasons_covered=False))["ok"] is False


def test_gate_refuses_live_execution():
    assert validate_p29_2_gate(_summary(tool_request_executed_live=True))["ok"] is False


def test_gate_refuses_belief_promotion():
    assert validate_p29_2_gate(_summary(belief_promotion_automatic=True))["ok"] is False
