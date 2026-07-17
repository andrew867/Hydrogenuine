"""AIS-7 patch hygiene planner tests."""

from __future__ import annotations

import pytest

from hg_runtime.agent_immune_system.ais7_gate import VERDICT_GREEN, validate_ais7_gate
from hg_runtime.agent_immune_system.patch_hygiene import (
    build_patch_hygiene_layer,
    replay_patch_hygiene_layer,
    validate_patch_request,
)
from hg_runtime.agent_immune_system.schemas import PHASE19_VERDICT, PHASE24_STATUS


def _gate_summary(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "ais6_green": True,
        "patch_candidate_requests_written": True,
        "rollback_plans_written": True,
        "vulnerability_finding_creates_patch_candidate_request": True,
        "patch_candidate_request_is_not_patch": True,
        "repair_recommendation_not_patch_permission": True,
        "operator_approval_required": True,
        "dry_run_apply_required_later": True,
        "rollback_plan_required": True,
        "no_automatic_patching": True,
        "no_live_mutation": True,
        "no_deployment": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_patch_request_hashes": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_ais7_vulnerability_finding_creates_patch_candidate_request():
    layer = build_patch_hygiene_layer()
    assert layer["manifest"]["source_finding_count"] > 0
    assert len(layer["requests"]) == layer["manifest"]["source_finding_count"]


def test_ais7_patch_candidate_request_is_not_patch():
    layer = build_patch_hygiene_layer()
    assert all(r["patch_candidate_request_is_not_patch"] for r in layer["requests"])
    assert all(not r["patch_applied"] for r in layer["requests"])


def test_ais7_repair_recommendation_not_patch_permission():
    layer = build_patch_hygiene_layer()
    assert all(r["repair_recommendation_is_not_patch_permission"] for r in layer["requests"])


def test_ais7_operator_approval_required():
    layer = build_patch_hygiene_layer()
    assert all(r["operator_approval_required"] for r in layer["requests"])


def test_ais7_dry_run_apply_required_later():
    layer = build_patch_hygiene_layer()
    assert all(r["dry_run_apply_required_later"] for r in layer["requests"])


def test_ais7_rollback_plan_required():
    layer = build_patch_hygiene_layer()
    assert len(layer["rollback_plans"]) == len(layer["requests"])
    assert all(p["rollback_required_before_apply"] for p in layer["rollback_plans"])


def test_ais7_no_automatic_patching():
    layer = build_patch_hygiene_layer()
    assert layer["manifest"]["automatic_patching_allowed"] is False


def test_ais7_no_live_mutation():
    layer = build_patch_hygiene_layer()
    assert all(not r["live_mutation_performed"] for r in layer["requests"])


def test_ais7_no_deployment():
    layer = build_patch_hygiene_layer()
    assert all(not r["candidate_deployed"] for r in layer["requests"])


def test_ais7_no_authority_grant():
    layer = build_patch_hygiene_layer()
    assert all(not r["authority_granted"] for r in layer["requests"])


def test_ais7_no_tool_authorization():
    layer = build_patch_hygiene_layer()
    assert all(not r["tools_authorized"] for r in layer["requests"])


def test_ais7_replay_preserves_patch_request_hashes():
    layer = build_patch_hygiene_layer()
    replay = replay_patch_hygiene_layer(layer["requests"], layer["rollback_plans"], layer["manifest"])
    assert replay["replay_preserves_patch_request_hashes"] is True


def test_ais7_replay_rejects_mutated_request():
    layer = build_patch_hygiene_layer()
    mutated = [dict(r) for r in layer["requests"]]
    mutated[0]["record_hash"] = "mutated"
    replay = replay_patch_hygiene_layer(mutated, layer["rollback_plans"], layer["manifest"])
    assert replay["replay_preserves_patch_request_hashes"] is False


def test_ais7_preserves_phase19_yellow():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")


def test_ais7_preserves_phase24_infrastructure_only():
    assert PHASE24_STATUS == "infrastructure_only"


def test_ais7_rejects_patch_laundering():
    layer = build_patch_hygiene_layer()
    bad = dict(layer["requests"][0])
    bad["patch_applied"] = True
    with pytest.raises(ValueError):
        validate_patch_request(bad)


def test_ais7_gate_passes_on_full_summary():
    assert validate_ais7_gate(_gate_summary())["ok"] is True


def test_ais7_gate_refuses_patch_apply():
    assert validate_ais7_gate(_gate_summary(patch_applied=True))["ok"] is False


def test_ais7_gate_refuses_missing_operator_approval():
    assert validate_ais7_gate(_gate_summary(operator_approval_required=False))["ok"] is False


def test_ais7_gate_refuses_live_mutation():
    assert validate_ais7_gate(_gate_summary(live_mutation_performed=True))["ok"] is False
