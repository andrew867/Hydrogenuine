"""Phase 25 advisory self-improvement schema foundation and boundary checks.

Phase 25 is advisory-only. Zero may read local report/proof summaries and emit
improvement proposals, risks, and operator review tasks. It may not patch,
self-authorize, merge, change authority, grant tools, apply changes, or mark
itself better. A proposal is not patch permission. A proposal is not
self-authorization.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash

PROVIDER_MODE = "FIXTURE_ONLY_LOCAL_ONLY"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

VERDICT_GREEN_PHASE25 = "GREEN_PHASE25_ADVISORY_SELF_IMPROVEMENT"
VERDICT_RED_PHASE25 = "RED_PHASE25_ADVISORY_SELF_IMPROVEMENT_FAILED"

PROPOSAL_CATEGORIES = {
    "COVERAGE_EXPANSION",
    "DOCUMENTATION",
    "OBSERVABILITY",
    "TEST_HARDENING",
    "GAP_RECONCILIATION",
    "OPERATOR_WORKFLOW",
}

RISK_LEVELS = {
    "LOW",
    "MEDIUM",
    "HIGH",
    "REQUIRES_OPERATOR_REVIEW",
}

# Forbidden requests Phase 25 must REFUSE (not implement).
REFUSAL_REASONS = {
    "DIRECT_PATCH_FORBIDDEN",
    "SELF_MERGE_FORBIDDEN",
    "PROVIDER_OR_WEB_FORBIDDEN",
    "PDF_OCR_FORBIDDEN",
    "AUTHORITY_GRANT_FORBIDDEN",
    "PHASE19_GREEN_FORBIDDEN",
    "PHASE24_FULL_GREEN_FORBIDDEN",
    "AUTOMATIC_BELIEF_PROMOTION_FORBIDDEN",
}

RECORD_TYPES = {
    "advisory_improvement_proposal_v1",
    "advisory_risk_record_v1",
    "advisory_operator_review_task_v1",
    "advisory_refusal_record_v1",
    "phase25_manifest_v1",
    "phase25_gate_result_v1",
}

STABLE_HASH_EXCLUDE = {
    "record_hash",
    "gate_hash",
    "manifest_hash",
    "analysis_hash",
    "created_at",
    "base_head",
    "proof_bundle",
}


class Phase25BoundaryError(ValueError):
    """Phase 25 advisory boundary violation."""


def neutral_flags() -> dict[str, bool]:
    return {
        "proposal_is_patch_permission": False,
        "proposal_is_self_authorization": False,
        "advisory_output_is_authority": False,
        "review_task_is_implementation": False,
        "self_merge_performed": False,
        "patch_applied": False,
        "patch_request_applied": False,
        "tools_authorized": False,
        "authority_granted": False,
        "authority_changed": False,
        "self_marked_better": False,
        "belief_promoted": False,
        "belief_promotion_automatic": False,
        "phase19_marked_green": False,
        "phase24_marked_full_green": False,
        "provider_enabled": False,
        "web_enabled": False,
        "pdf_ocr_enabled": False,
        "html_parsing_enabled": False,
        "arbitrary_file_ingestion_enabled": False,
        "web_browse_performed": False,
        "external_provider_calls_made": False,
        "live_external_side_effects_created": False,
        "deletion_performed": False,
        "truth_claimed": False,
        "secrets_emitted": False,
    }


FORBIDDEN_TRUE = set(neutral_flags())


def record_hash(record: Mapping[str, Any]) -> str:
    return canonical_hash({k: v for k, v in record.items() if k not in STABLE_HASH_EXCLUDE})


def assert_neutral(record: Mapping[str, Any]) -> None:
    for key, value in record.items():
        if key in FORBIDDEN_TRUE and value:
            raise Phase25BoundaryError(f"forbidden_true:{key}")
        if isinstance(value, Mapping):
            assert_neutral(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    assert_neutral(item)


def with_hash(record: dict, hash_field: str = "record_hash") -> dict:
    record[hash_field] = record_hash(record)
    assert_neutral(record)
    return record
