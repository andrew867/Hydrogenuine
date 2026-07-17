"""AIS-7 patch hygiene planner."""

from __future__ import annotations

from hg_runtime.agent_immune_system.hashing import record_hash
from hg_runtime.agent_immune_system.patch_request import build_patch_candidate_request
from hg_runtime.agent_immune_system.rollback_plan import build_rollback_plan
from hg_runtime.agent_immune_system.schemas import PHASE19_VERDICT, PHASE24_STATUS, assert_neutral, neutral_flags
from hg_runtime.agent_immune_system.security_audit import build_security_audit_layer


def build_patch_hygiene_layer() -> dict:
    security_layer = build_security_audit_layer()
    selected_findings = security_layer["findings"][:5]
    requests = [
        build_patch_candidate_request(
            request_id=f"phr-{finding['finding_id']}",
            source_finding_id=finding["finding_id"],
            finding_type=finding["finding_type"],
            requested_scope=finding["surface"],
        )
        for finding in selected_findings
    ]
    rollback_plans = [
        build_rollback_plan(rollback_plan_id=f"rb-{request['request_id']}", request_id=request["request_id"])
        for request in requests
    ]
    manifest = {
        "schema_version": "1",
        "record_type": "patch_hygiene_manifest_v1",
        "manifest_id": "ais7-patch-hygiene-planner",
        "source_finding_count": len(selected_findings),
        "patch_candidate_request_count": len(requests),
        "rollback_plan_count": len(rollback_plans),
        "request_hashes": [r["record_hash"] for r in requests],
        "rollback_plan_hashes": [r["record_hash"] for r in rollback_plans],
        "patch_candidate_request_is_not_patch": True,
        "repair_recommendation_is_not_patch_permission": True,
        "operator_approval_required": True,
        "dry_run_apply_required_later": True,
        "rollback_plan_required": True,
        "automatic_patching_allowed": False,
        "live_mutation_performed": False,
        "candidate_deployed": False,
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)
    replay = replay_patch_hygiene_layer(requests, rollback_plans, manifest)
    return {
        "source_findings": selected_findings,
        "requests": requests,
        "rollback_plans": rollback_plans,
        "manifest": manifest,
        "replay": replay,
    }


def replay_patch_hygiene_layer(requests: list[dict], rollback_plans: list[dict], manifest: dict) -> dict:
    failures: list[str] = []
    if [r["record_hash"] for r in requests] != manifest.get("request_hashes", []):
        failures.append("request_hash_list_mismatch")
    if [r["record_hash"] for r in rollback_plans] != manifest.get("rollback_plan_hashes", []):
        failures.append("rollback_hash_list_mismatch")
    for record in requests + rollback_plans:
        assert_neutral(record)
        expected = record_hash({k: v for k, v in record.items() if k != "record_hash"})
        if record["record_hash"] != expected:
            failures.append(f"record_hash_mismatch:{record.get('request_id') or record.get('rollback_plan_id')}")
    return {
        "schema_version": "1",
        "record_type": "patch_hygiene_replay_record_v1",
        "replay_id": "ais7-patch-hygiene-replay",
        "replay_preserves_patch_request_hashes": not failures,
        "failures": failures,
        **neutral_flags(),
    }


def validate_patch_request(request: dict) -> None:
    assert_neutral(request)
    if request.get("patch_applied") or request.get("live_mutation_performed") or request.get("candidate_deployed"):
        raise ValueError("patch_hygiene_cannot_apply_or_deploy")
    if not request.get("operator_approval_required"):
        raise ValueError("operator_approval_required")
