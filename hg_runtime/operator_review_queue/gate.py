"""Phase 41 gate validation."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.operator_review_queue.schemas import VERDICT_RED


def validate_phase41_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    for phase in ("phase40", "phase39", "phase38", "phase37", "phase35"):
        if not result.get(f"{phase}_green"):
            failures.append(f"phase41_gate_requires_{phase}_green")
    checks = {
        "safe_doc_candidate_queued": "safe_doc_candidate_not_queued",
        "safe_test_candidate_queued": "safe_test_candidate_not_queued",
        "operator_permit_required_for_apply": "operator_permit_required",
        "apply_without_operator_permit_rejected": "missing_permit_not_rejected",
        "self_issued_operator_permit_rejected": "self_issued_permit_not_rejected",
        "invalid_operator_permit_rejected": "invalid_permit_not_rejected",
        "valid_operator_permit_fixture_accepted": "valid_permit_not_accepted",
        "dry_run_apply_completed": "dry_run_apply_not_completed",
        "dry_run_apply_sandbox_only": "dry_run_not_sandbox_only",
        "rollback_tested": "rollback_not_tested",
        "phase19_yellow_preserved": "phase19_not_yellow",
        "phase40_repair_preserved": "phase40_repair_not_preserved",
        "phase24_infrastructure_only_preserved": "phase24_not_infrastructure_only",
        "replay_preserves_queue_and_apply_receipts": "replay_required",
        "proof_bundle_valid": "proof_bundle_required",
        "report_present": "report_required",
        "fake_green_live_apply_rejected": "fake_green_live_apply_not_rejected",
    }
    for key, msg in checks.items():
        if not result.get(key):
            failures.append(msg)
    for key in ("queue_entry_is_approval", "live_repo_mutated", "patch_candidates_applied_to_live_repo", "patch_candidates_committed", "patch_candidates_pushed", "patch_candidates_deployed", "authority_granted", "tools_authorized", "live_external_side_effects_created", "external_provider_calls_made"):
        if result.get(key):
            failures.append(key)
    return {"ok": not failures and result.get("verdict") != VERDICT_RED, "failures": failures}
