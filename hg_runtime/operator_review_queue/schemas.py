"""Phase 41 operator review queue schemas and hard boundaries."""

from __future__ import annotations

from typing import Any, Mapping

QUEUE_ITEM_SCHEMA = "operator_review_queue_item_v1"
QUEUE_MANIFEST_SCHEMA = "operator_review_queue_manifest_v1"
PERMIT_FIXTURE_SCHEMA = "operator_permit_fixture_v1"
PERMIT_VALIDATION_SCHEMA = "operator_permit_validation_v1"
DRY_RUN_REQUEST_SCHEMA = "patch_apply_dry_run_request_v1"
DRY_RUN_RESULT_SCHEMA = "patch_apply_dry_run_result_v1"
SANDBOX_RECORD_SCHEMA = "disposable_sandbox_record_v1"
ROLLBACK_RECORD_SCHEMA = "rollback_record_v1"
LIVE_REPO_AUDIT_SCHEMA = "live_repo_mutation_audit_v1"
REVIEW_DECISION_SCHEMA = "operator_review_decision_v1"
REPLAY_RECORD_SCHEMA = "operator_review_replay_record_v1"
GATE_RESULT_SCHEMA = "operator_review_gate_result_v1"

VERDICT_GREEN = "GREEN_PHASE41_OPERATOR_REVIEW_QUEUE_PATCH_APPLY_DRY_RUN"
VERDICT_YELLOW = "YELLOW_PHASE41_OPERATOR_REVIEW_QUEUE_PARTIAL"
VERDICT_RED = "RED_PHASE41_OPERATOR_REVIEW_QUEUE_FAILED"

QUEUED_FOR_OPERATOR_REVIEW = "QUEUED_FOR_OPERATOR_REVIEW"
REJECTED_NOT_SAFE_TO_REVIEW = "REJECTED_NOT_SAFE_TO_REVIEW"
REJECTED_NO_OPERATOR_PERMIT = "REJECTED_NO_OPERATOR_PERMIT"
REJECTED_SELF_ISSUED_PERMIT = "REJECTED_SELF_ISSUED_PERMIT"
REJECTED_INVALID_PERMIT = "REJECTED_INVALID_PERMIT"
DRY_RUN_APPLY_COMPLETED = "DRY_RUN_APPLY_COMPLETED"
DRY_RUN_APPLY_ROLLED_BACK = "DRY_RUN_APPLY_ROLLED_BACK"
REJECTED_LIVE_REPO_MUTATION = "REJECTED_LIVE_REPO_MUTATION"
REJECTED_EXTERNAL_SIDE_EFFECT_RISK = "REJECTED_EXTERNAL_SIDE_EFFECT_RISK"

PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"


class OperatorReviewQueueError(ValueError):
    """Phase 41 validation or boundary refusal."""


def neutral_flags() -> dict[str, bool]:
    return {
        "authority_granted": False,
        "tools_authorized": False,
        "live_effects_created": False,
        "external_provider_calls_made": False,
        "new_live_posts_created": False,
        "candidate_committed": False,
        "candidate_pushed": False,
        "candidate_deployed": False,
        "live_repo_mutated": False,
        "patch_candidates_applied_to_live_repo": False,
        "claims_agi": False,
    }


FORBIDDEN_TRUE = {
    "authority_granted": "authority_granted",
    "tools_authorized": "tools_authorized",
    "live_effects_created": "live_effect_created",
    "external_provider_calls_made": "external_provider_call",
    "new_live_posts_created": "live_post_created",
    "candidate_committed": "candidate_committed",
    "candidate_pushed": "candidate_pushed",
    "candidate_deployed": "candidate_deployed",
    "live_repo_mutated": "live_repo_mutated",
    "patch_candidates_applied_to_live_repo": "live_repo_patch_applied",
    "claims_agi": "claims_agi_forbidden",
}


def assert_neutral(payload: Mapping[str, Any]) -> None:
    for key, value in payload.items():
        if value and str(key) in FORBIDDEN_TRUE:
            raise OperatorReviewQueueError(FORBIDDEN_TRUE[str(key)])
        if isinstance(value, Mapping):
            assert_neutral(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    assert_neutral(item)
