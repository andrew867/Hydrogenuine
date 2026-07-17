"""ORP schemas and neutral boundary constants."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash

PHASE_ID_ORP0 = "ORP-0"
VERDICT_GREEN_ORP0 = "GREEN_ORP_0_OPERATOR_REVIEW_SCHEMAS"
VERDICT_RED_ORP0 = "RED_ORP_0_OPERATOR_REVIEW_SCHEMAS_FAILED"
PROVIDER_MODE = "FIXTURE_ONLY_LOCAL_ONLY"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

DECISION_STATUSES = (
    "APPROVE_FOR_PROVISIONAL_USE",
    "REJECT_SOURCE",
    "REQUEST_MORE_EVIDENCE",
    "DEFER_REVIEW",
    "QUARANTINE_RECOMMENDED",
    "RETRACTION_RECOMMENDED",
)

RECORD_TYPES = {
    "operator_review_decision_v1",
    "operator_review_manifest_v1",
    "evidence_promotion_request_v1",
    "promotion_gate_result_v1",
    "promotion_policy_receipt_v1",
    "reviewed_evidence_link_v1",
    "operator_rejection_record_v1",
    "operator_deferral_record_v1",
    "operator_review_replay_record_v1",
}


class OperatorReviewPromotionError(ValueError):
    """Operator review / promotion boundary violation."""


def neutral_flags() -> dict[str, bool]:
    return {
        "operator_review_treated_as_truth": False,
        "evidence_treated_as_truth": False,
        "truth_claimed": False,
        "operator_approval_is_action_permission": False,
        "authority_granted": False,
        "tools_authorized": False,
        "web_authorized": False,
        "providers_authorized": False,
        "web_browse_performed": False,
        "external_provider_calls_made": False,
        "live_external_side_effects_created": False,
        "belief_promoted": False,
        "belief_promotion_automatic": False,
        "promotion_request_is_promotion": False,
        "promotion_gate_is_truth": False,
        "deletion_performed": False,
        "patch_request_applied": False,
        "arbitrary_file_ingestion_enabled": False,
        "pdf_ingestion_enabled": False,
        "secrets_emitted": False,
    }


FORBIDDEN_TRUE = set(neutral_flags())


def record_hash(record: Mapping[str, Any]) -> str:
    return canonical_hash(
        {
            k: v
            for k, v in record.items()
            if k not in {"record_hash", "receipt_hash", "manifest_hash", "decision_hash", "request_hash", "gate_hash"}
        }
    )


def assert_neutral(record: Mapping[str, Any]) -> None:
    for key, value in record.items():
        if key in FORBIDDEN_TRUE and value:
            raise OperatorReviewPromotionError(f"forbidden_true:{key}")
        if isinstance(value, Mapping):
            assert_neutral(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    assert_neutral(item)
