"""P26 experience-ledger gap reconciliation schema foundation.

Gap analysis is NOT completion. Partial satisfaction is NOT GREEN for P26.
Existing artifacts do NOT auto-complete P26. This module only maps the P26
acceptance criteria onto existing runtime artifacts and records gaps and
recommendations. The GREEN verdict attests that the *reconciliation* ran, never
that P26 itself is complete.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash

PROVIDER_MODE = "FIXTURE_ONLY_LOCAL_ONLY"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

VERDICT_GREEN_P26_GAP = "GREEN_P26_EXPERIENCE_LEDGER_GAP_RECONCILIATION"
VERDICT_RED_P26_GAP = "RED_P26_EXPERIENCE_LEDGER_GAP_RECONCILIATION_FAILED"

GAP_STATUSES = {
    "SATISFIED_BY_EXISTING_ARTIFACT",
    "PARTIALLY_SATISFIED",
    "MISSING",
    "INCOMPATIBLE",
    "OUT_OF_SCOPE",
    "REQUIRES_EXACT_P26_IMPLEMENTATION",
}

# Statuses that, alone, can never be read as completion of a P26 criterion.
NON_COMPLETING_STATUSES = {
    "PARTIALLY_SATISFIED",
    "MISSING",
    "INCOMPATIBLE",
    "OUT_OF_SCOPE",
    "REQUIRES_EXACT_P26_IMPLEMENTATION",
}

RECORD_TYPES = {
    "p26_acceptance_criterion_v1",
    "p26_existing_artifact_map_entry_v1",
    "p26_gap_record_v1",
    "p26_recommendation_record_v1",
    "p26_reconciliation_manifest_v1",
    "p26_gap_gate_result_v1",
}

STABLE_HASH_EXCLUDE = {
    "record_hash",
    "gate_hash",
    "manifest_hash",
    "created_at",
    "base_head",
    "proof_bundle",
}


class P26GapBoundaryError(ValueError):
    """P26 gap reconciliation boundary violation."""


def neutral_flags() -> dict[str, bool]:
    return {
        "gap_analysis_is_completion": False,
        "partial_satisfaction_is_green": False,
        "existing_artifact_auto_completes_p26": False,
        "p26_marked_complete": False,
        "authority_changed": False,
        "authority_granted": False,
        "tools_authorized": False,
        "new_ingestion_enabled": False,
        "arbitrary_file_ingestion_enabled": False,
        "pdf_ocr_enabled": False,
        "html_parsing_enabled": False,
        "belief_promoted": False,
        "belief_promotion_automatic": False,
        "deletion_performed": False,
        "patch_request_applied": False,
        "web_browse_performed": False,
        "external_provider_calls_made": False,
        "live_external_side_effects_created": False,
        "truth_claimed": False,
        "secrets_emitted": False,
    }


FORBIDDEN_TRUE = set(neutral_flags())


def record_hash(record: Mapping[str, Any]) -> str:
    return canonical_hash({k: v for k, v in record.items() if k not in STABLE_HASH_EXCLUDE})


def assert_neutral(record: Mapping[str, Any]) -> None:
    for key, value in record.items():
        if key in FORBIDDEN_TRUE and value:
            raise P26GapBoundaryError(f"forbidden_true:{key}")
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
