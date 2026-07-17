"""LEB-0 schemas and boundary constants."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash

PHASE_ID = "LEB-0"
VERDICT_GREEN = "GREEN_LEB_0_SCHEMA_BOUNDARY"
VERDICT_RED = "RED_LEB_0_SCHEMA_BOUNDARY_FAILED"
GATE_RESULT_SCHEMA = "evidence_ingestion_gate_result_v1"
PROVIDER_MODE = "FIXTURE_ONLY_LOCAL_ONLY"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

RECORD_TYPES = {
    "operator_provided_source_v1",
    "local_source_manifest_v1",
    "local_evidence_receipt_v1",
    "source_excerpt_receipt_v1",
    "evidence_redaction_record_v1",
    "evidence_boundary_receipt_v1",
    "evidence_ingestion_request_v1",
    "evidence_ingestion_gate_result_v1",
}


class EvidenceBridgeError(ValueError):
    """Local evidence bridge boundary violation."""


def neutral_flags() -> dict[str, bool]:
    return {
        "truth_claimed": False,
        "authority_granted": False,
        "tools_authorized": False,
        "belief_promoted": False,
        "ingestion_permission_granted": False,
        "web_browse_performed": False,
        "external_provider_calls_made": False,
        "live_external_side_effects_created": False,
        "arbitrary_path_access_enabled": False,
        "path_traversal_allowed": False,
        "secrets_emitted": False,
    }


FORBIDDEN_TRUE = {
    "truth_claimed",
    "authority_granted",
    "tools_authorized",
    "belief_promoted",
    "ingestion_permission_granted",
    "web_browse_performed",
    "external_provider_calls_made",
    "live_external_side_effects_created",
    "arbitrary_path_access_enabled",
    "path_traversal_allowed",
    "secrets_emitted",
}


def record_hash(record: Mapping[str, Any]) -> str:
    return canonical_hash({k: v for k, v in record.items() if k not in {"record_hash", "receipt_hash", "manifest_hash"}})


def assert_neutral(record: Mapping[str, Any]) -> None:
    for key, value in record.items():
        if key in FORBIDDEN_TRUE and value:
            raise EvidenceBridgeError(f"forbidden_true:{key}")
        if isinstance(value, Mapping):
            assert_neutral(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    assert_neutral(item)
