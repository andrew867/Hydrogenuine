"""OES schema foundation and boundary checks."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash

PROVIDER_MODE = "FIXTURE_ONLY_LOCAL_ONLY"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

SOAK_ITERATION_COUNT = 5

VERDICT_GREEN_OES0 = "GREEN_OES_0_SCHEMA_POLICY"
VERDICT_RED_OES0 = "RED_OES_0_SCHEMA_POLICY_FAILED"
VERDICT_GREEN_OES1 = "GREEN_OES_1_REPEATED_CORPUS_REPLAY_SOAK"
VERDICT_RED_OES1 = "RED_OES_1_REPEATED_CORPUS_REPLAY_SOAK_FAILED"
VERDICT_GREEN_OES2 = "GREEN_OES_2_MUTATION_REPLAY_MISMATCH_DETECTOR"
VERDICT_RED_OES2 = "RED_OES_2_MUTATION_REPLAY_MISMATCH_DETECTOR_FAILED"
VERDICT_GREEN_OES3 = "GREEN_OES_3_AIS_FEVER_QUARANTINE_STRESS"
VERDICT_RED_OES3 = "RED_OES_3_AIS_FEVER_QUARANTINE_STRESS_FAILED"
VERDICT_GREEN_OES_CONSOLIDATION = "GREEN_OES_OPERATOR_EVIDENCE_SOAK_CONSOLIDATION"
VERDICT_RED_OES_CONSOLIDATION = "RED_OES_OPERATOR_EVIDENCE_SOAK_CONSOLIDATION_FAILED"

MUTATION_PROBE_TYPES = {
    "MODIFIED_CORPUS_SOURCE_HASH",
    "MODIFIED_EVIDENCE_RECEIPT_HASH",
    "MODIFIED_PACKET_SUPPORT_RECORD",
    "MODIFIED_SECOND_SOURCE_RESULT",
    "MODIFIED_CONTRADICTION_PACKET",
    "MODIFIED_DASHBOARD_SUMMARY",
    "REMOVED_RECEIPT_CHAIN_ENTRY",
    "ALTERED_BOUNDARY_ASSERTION",
}

RECORD_TYPES = {
    "operator_evidence_soak_v1",
    "soak_policy_v1",
    "soak_manifest_v1",
    "soak_iteration_result_v1",
    "soak_replay_result_v1",
    "soak_boundary_assertion_v1",
    "soak_mutation_probe_v1",
    "soak_mutation_result_v1",
    "soak_gate_result_v1",
}

STABLE_HASH_EXCLUDE = {
    "record_hash",
    "gate_hash",
    "manifest_hash",
    "soak_hash",
    "packet_hash",
    "dashboard_hash",
    "receipt_hash",
    "content_hash",
    "created_at",
    "base_head",
    "proof_bundle",
    "iteration_started_at",
    "iteration_completed_at",
}


class OESBoundaryError(ValueError):
    """OES truth, authority, or side-effect boundary violation."""


def neutral_flags() -> dict[str, bool]:
    return {
        "soak_treated_as_truth": False,
        "replay_match_treated_as_truth": False,
        "determinism_treated_as_correctness": False,
        "mutation_detection_is_repair": False,
        "mutation_auto_repaired": False,
        "corpus_treated_as_truth": False,
        "expected_outcome_treated_as_proof": False,
        "packet_treated_as_truth": False,
        "dashboard_treated_as_operator_approval": False,
        "quarantine_candidate_is_deletion": False,
        "patch_hygiene_task_is_patch": False,
        "fever_unlocks_action": False,
        "truth_claimed": False,
        "certainty_claimed": False,
        "authority_granted": False,
        "tools_authorized": False,
        "web_browse_performed": False,
        "external_provider_calls_made": False,
        "live_external_side_effects_created": False,
        "belief_promoted": False,
        "belief_promotion_automatic": False,
        "deletion_performed": False,
        "patch_request_applied": False,
        "arbitrary_file_ingestion_enabled": False,
        "pdf_ingestion_enabled": False,
        "directory_crawling_enabled": False,
        "old_proof_mutated": False,
        "secrets_emitted": False,
    }


FORBIDDEN_TRUE = set(neutral_flags())


def record_hash(record: Mapping[str, Any]) -> str:
    return canonical_hash(
        {
            k: v
            for k, v in record.items()
            if k not in STABLE_HASH_EXCLUDE
        }
    )


def assert_neutral(record: Mapping[str, Any]) -> None:
    for key, value in record.items():
        if key in FORBIDDEN_TRUE and value:
            raise OESBoundaryError(f"forbidden_true:{key}")
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
