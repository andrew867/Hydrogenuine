"""P29-1 tool plan builder — builds tool plans from P28 domain packs."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.domain_pack_runtime.domain_pack_builder import build_domain_packs
from hg_runtime.tool_mediated_workbench.domain_pack_tool_mapper import (
    identify_capability_gaps,
    map_domain_pack_to_tool_requests,
)
from hg_runtime.tool_mediated_workbench.hashing import with_hash
from hg_runtime.tool_mediated_workbench.schemas import (
    PHASE19_VERDICT,
    PHASE24_STATUS,
    P29_INVARIANTS,
    assert_neutral,
    neutral_flags,
)
from hg_runtime.tool_mediated_workbench.tool_plan import build_tool_plan
from hg_runtime.tool_mediated_workbench.tool_workbench_policy import build_tool_workbench_policy


def build_p28_domain_pack_manifest(repo_root: Path) -> dict:
    layer = build_domain_packs(repo_root)
    manifest = {
        "record_type": "p29_p28_domain_pack_manifest_v1",
        "schema_version": "1",
        "manifest_id": "p29-1-p28-domain-pack-manifest",
        "explicit_manifest_only": True,
        "domain_pack_count": len(layer["domain_packs"]),
        "pack_ids": [p["pack_id"] for p in layer["domain_packs"]],
        "domain_pack_treated_as_permission": False,
        "domain_pack_treated_as_tool_permission": False,
    }
    with_hash(manifest, "manifest_hash")
    assert_neutral(manifest)
    return {**layer, "p28_manifest": manifest}


def build_tool_plan_layer(repo_root: Path) -> dict:
    p28_layer = build_p28_domain_pack_manifest(repo_root)
    policy = build_tool_workbench_policy()
    packs = p28_layer["domain_packs"]

    plans = []
    all_requests = []
    all_gaps = []

    for pack in packs:
        requests = map_domain_pack_to_tool_requests(pack=pack, request_id_prefix="req-plan")
        all_requests.extend(requests)
        gaps = identify_capability_gaps(pack)
        all_gaps.extend(gaps)
        plan = build_tool_plan(
            plan_id=f"plan-{pack['pack_id']}",
            domain_pack_id=pack["pack_id"],
            skill_ids=list(pack.get("skill_ids", [])),
            tool_requests=requests,
            provenance_refs=list(pack.get("provenance_refs", [])),
            capability_gaps=gaps,
        )
        plans.append(plan)

    manifest = {
        "record_type": "tool_plan_builder_manifest_v1",
        "schema_version": "1",
        "manifest_id": "p29-1-tool-plan-builder",
        "repo_root": str(repo_root),
        "plan_count": len(plans),
        "request_count": len(all_requests),
        "gap_count": len(all_gaps),
        "p28_manifest_hash": p28_layer["p28_manifest"]["manifest_hash"],
        "explicit_manifest_only": True,
        "invariants": P29_INVARIANTS,
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        "tool_plan_is_not_permission": True,
        "domain_pack_does_not_grant_tools": True,
        "tool_plan_treated_as_permission": False,
        "tool_request_executed_live": False,
        "domain_pack_treated_as_tool_permission": False,
        "tool_authorization_granted": False,
        "belief_promotion_automatic": False,
    }
    with_hash(manifest, "manifest_hash")
    assert_neutral(manifest)

    return {
        "policy": policy,
        "plans": plans,
        "requests": all_requests,
        "capability_gaps": all_gaps,
        "p28_manifest": p28_layer["p28_manifest"],
        "manifest": manifest,
    }


def replay_tool_plan_layer(repo_root: Path, expected_manifest_hash: str, expected_plan_hashes: list[str]) -> dict:
    layer = build_tool_plan_layer(repo_root)
    actual_plan_hashes = [p["plan_hash"] for p in layer["plans"]]
    return {
        "replay_preserves_manifest_hash": layer["manifest"]["manifest_hash"] == expected_manifest_hash,
        "replay_preserves_plan_hashes": actual_plan_hashes == expected_plan_hashes,
        "replayed_manifest_hash": layer["manifest"]["manifest_hash"],
        "expected_manifest_hash": expected_manifest_hash,
    }
