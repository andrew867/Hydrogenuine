"""Deterministic P29-0 schema fixtures."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.tool_mediated_workbench.hashing import stable_hash, with_hash
from hg_runtime.tool_mediated_workbench.schemas import (
    PHASE19_VERDICT,
    PHASE24_STATUS,
    P29_INVARIANTS,
    REFUSAL_REASONS,
    assert_neutral,
)
from hg_runtime.tool_mediated_workbench.tool_plan import build_tool_plan
from hg_runtime.tool_mediated_workbench.tool_receipt import build_tool_receipt
from hg_runtime.tool_mediated_workbench.tool_request import build_tool_request
from hg_runtime.tool_mediated_workbench.tool_sandbox import build_sandbox_result
from hg_runtime.tool_mediated_workbench.tool_workbench_policy import build_tool_workbench_policy


def build_p29_0_layer(repo_root: Path) -> dict:
    policy = build_tool_workbench_policy()

    req_read = build_tool_request(
        request_id="req-fixture-read-001",
        request_type="local_read",
        tool_name="read_artifact",
        description="Read a local artifact for analysis",
        domain_pack_id="pack-fixture-sle_rc",
        skill_id="skill-fixture-001",
        provenance_refs=["rc_artifact_index.json"],
    )
    req_write = build_tool_request(
        request_id="req-fixture-write-001",
        request_type="local_write",
        tool_name="write_report",
        description="Write a local report artifact",
        domain_pack_id="pack-fixture-sle_rc",
    )

    plan = build_tool_plan(
        plan_id="plan-fixture-001",
        domain_pack_id="pack-fixture-sle_rc",
        skill_ids=["skill-fixture-001"],
        tool_requests=[req_read, req_write],
        provenance_refs=["rc_artifact_index.json", "rc_boundary_matrix.json"],
        capability_gaps=["web_search_not_available"],
    )

    sandbox_ok = build_sandbox_result(
        sandbox_id="sandbox-fixture-001",
        request_id=req_read["request_id"],
        plan_id=plan["plan_id"],
        result_state="DRY_RUN_COMPLETE",
        simulated_output="fixture_read_output",
    )
    sandbox_refused = build_sandbox_result(
        sandbox_id="sandbox-fixture-002",
        request_id=req_write["request_id"],
        plan_id=plan["plan_id"],
        result_state="REFUSED_BY_POLICY",
        refusal_reason="filesystem_write_request",
    )

    receipt = build_tool_receipt(
        receipt_id="receipt-fixture-001",
        plan_id=plan["plan_id"],
        sandbox_result_ids=[sandbox_ok["sandbox_id"], sandbox_refused["sandbox_id"]],
        refusal_ids=["refusal-fixture-002"],
    )

    records = [policy, req_read, req_write, plan, sandbox_ok, sandbox_refused, receipt]
    manifest = {
        "record_type": "tool_workbench_manifest_v1",
        "schema_version": "1",
        "manifest_id": "p29-0-schema-fixture",
        "repo_root": str(repo_root),
        "record_count": len(records),
        "invariants": P29_INVARIANTS,
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        "explicit_manifest_only": True,
        "tool_plan_treated_as_permission": False,
        "tool_request_executed_live": False,
        "sandbox_result_treated_as_live": False,
        "tool_authorization_granted": False,
        "belief_promotion_automatic": False,
    }
    with_hash(manifest, "manifest_hash")
    assert_neutral(manifest)

    return {
        "policy": policy,
        "requests": [req_read, req_write],
        "plans": [plan],
        "sandbox_results": [sandbox_ok, sandbox_refused],
        "receipts": [receipt],
        "manifest": manifest,
    }


def replay_p29_0(repo_root: Path, expected_manifest_hash: str) -> dict:
    layer = build_p29_0_layer(repo_root)
    return {
        "replay_preserves_manifest_hash": layer["manifest"]["manifest_hash"] == expected_manifest_hash,
        "replayed_manifest_hash": layer["manifest"]["manifest_hash"],
        "expected_manifest_hash": expected_manifest_hash,
    }
