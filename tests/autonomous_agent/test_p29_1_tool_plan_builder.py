"""P29-1 tool plan builder tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_runtime.tool_mediated_workbench.domain_pack_tool_mapper import (
    identify_capability_gaps,
    map_domain_pack_to_tool_requests,
)
from hg_runtime.tool_mediated_workbench.redaction import secret_scan
from hg_runtime.tool_mediated_workbench.schemas import (
    FORBIDDEN_TRUE,
    ToolWorkbenchBoundaryError,
)
from hg_runtime.tool_mediated_workbench.tool_plan_builder import (
    build_tool_plan_layer,
    replay_tool_plan_layer,
)
from hg_runtime.tool_mediated_workbench.workbench_gate import validate_p29_1_gate

ROOT = Path(__file__).resolve().parents[2]


# --- Domain pack tool mapper ------------------------------------------------

def test_mapper_produces_requests():
    pack = {
        "pack_id": "pack-sle_rc",
        "domain_label": "SLE-RC",
        "skill_ids": ["s1"],
        "provenance_refs": ["ref1"],
    }
    reqs = map_domain_pack_to_tool_requests(pack=pack)
    assert len(reqs) >= 1
    for r in reqs:
        assert r["record_type"] == "tool_request_v1"
        assert r["tool_request_is_not_execution"] is True


def test_mapper_unknown_domain_gets_default():
    pack = {
        "pack_id": "pack-new",
        "domain_label": "NOVELTY",
        "skill_ids": ["s1"],
        "provenance_refs": [],
    }
    reqs = map_domain_pack_to_tool_requests(pack=pack)
    assert len(reqs) >= 1


def test_capability_gaps_include_web_and_provider():
    pack = {"domain_label": "SLE-RC", "capability_refs": ["cap-sle"]}
    gaps = identify_capability_gaps(pack)
    assert any("web_fetch" in g for g in gaps)
    assert any("external_provider" in g for g in gaps)


def test_capability_gaps_include_missing_refs():
    pack = {"domain_label": "SLE-RC", "capability_refs": []}
    gaps = identify_capability_gaps(pack)
    assert any("no_capability" in g for g in gaps)


# --- Tool plan layer ---------------------------------------------------------

def test_layer_builds():
    layer = build_tool_plan_layer(ROOT)
    assert layer["plans"]
    assert layer["requests"]
    assert layer["capability_gaps"]
    assert layer["manifest"]["tool_plan_is_not_permission"] is True
    assert layer["manifest"]["domain_pack_does_not_grant_tools"] is True


def test_layer_explicit_manifest_only():
    layer = build_tool_plan_layer(ROOT)
    assert layer["manifest"]["explicit_manifest_only"] is True


def test_layer_consumes_p28_manifest():
    layer = build_tool_plan_layer(ROOT)
    assert layer["p28_manifest"]
    assert layer["manifest"]["p28_manifest_hash"]


def test_layer_all_plans_require_approval():
    layer = build_tool_plan_layer(ROOT)
    for plan in layer["plans"]:
        assert plan["requires_operator_approval"] is True


def test_layer_neutral_flags():
    layer = build_tool_plan_layer(ROOT)
    for plan in layer["plans"]:
        for flag in FORBIDDEN_TRUE:
            assert plan.get(flag, False) is False, f"{flag} True in {plan['plan_id']}"


def test_layer_rejects_domain_pack_as_permission():
    layer = build_tool_plan_layer(ROOT)
    assert layer["manifest"]["domain_pack_treated_as_tool_permission"] is False


# --- Replay ------------------------------------------------------------------

def test_replay_deterministic():
    layer = build_tool_plan_layer(ROOT)
    replay = replay_tool_plan_layer(
        ROOT,
        layer["manifest"]["manifest_hash"],
        [p["plan_hash"] for p in layer["plans"]],
    )
    assert replay["replay_preserves_manifest_hash"] is True
    assert replay["replay_preserves_plan_hashes"] is True


def test_replay_detects_mutation():
    replay = replay_tool_plan_layer(ROOT, "mutated", ["mutated"])
    assert replay["replay_preserves_manifest_hash"] is False


# --- Redaction ---------------------------------------------------------------

def test_secret_scan_passes():
    layer = build_tool_plan_layer(ROOT)
    assert secret_scan(layer) is True


# --- Gate --------------------------------------------------------------------

def _summary(**overrides):
    data = {
        "p29_0_green": True,
        "p28_consolidation_green": True,
        "explicit_manifest_only": True,
        "tool_plans_built": True,
        "capability_gaps_recorded": True,
        "operator_approval_required": True,
        "tool_plan_not_permission": True,
        "tool_request_not_execution": True,
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


def test_gate_passes():
    assert validate_p29_1_gate(_summary())["ok"] is True


def test_gate_refuses_missing_p29_0():
    assert validate_p29_1_gate(_summary(p29_0_green=False))["ok"] is False


def test_gate_refuses_missing_p28():
    assert validate_p29_1_gate(_summary(p28_consolidation_green=False))["ok"] is False


def test_gate_refuses_tool_authorization():
    assert validate_p29_1_gate(_summary(tool_authorization_granted=True))["ok"] is False


def test_gate_refuses_domain_pack_as_permission():
    assert validate_p29_1_gate(_summary(domain_pack_treated_as_tool_permission=True))["ok"] is False


def test_gate_refuses_live_execution():
    assert validate_p29_1_gate(_summary(tool_request_executed_live=True))["ok"] is False
