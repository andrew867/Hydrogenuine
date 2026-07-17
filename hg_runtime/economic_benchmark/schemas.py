"""Phase 34 economic-task-benchmark schemas and claim/authority guardrails.

A benchmark result is evidence, not authority. A benchmark pass is not permission,
not deployment approval, not a live-action permit, and not broad competence. A
benchmark report can never claim AGI, human-level economic capability, or the
ability to perform any economic task a human can. A benchmark case only supports
claims inside the tested, held-out, verified scope. Every record in this phase may
*measure, record, verify, or remember* -- never grant authority, authorize a tool,
widen a claim, or create a live side effect.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from hg_runtime.memory_ledger.schemas import OperationControl

BENCHMARK_SUITE_SCHEMA = "benchmark_suite_v1"
ECONOMIC_TASK_CASE_SCHEMA = "economic_task_case_v1"
BENCHMARK_TASK_DOMAIN_MAPPING_SCHEMA = "benchmark_task_domain_mapping_v1"
BENCHMARK_ARTIFACT_SCHEMA = "benchmark_artifact_v1"
ARTIFACT_HASH_RECORD_SCHEMA = "artifact_hash_record_v1"
BENCHMARK_VERIFIER_SCHEMA = "benchmark_verifier_v1"
VERIFICATION_RESULT_SCHEMA = "verification_result_v1"
EVIDENCE_QUALITY_RECORD_SCHEMA = "evidence_quality_record_v1"
BENCHMARK_COST_RECORD_SCHEMA = "benchmark_cost_record_v1"
MODEL_COST_RECORD_SCHEMA = "model_cost_record_v1"
BENCHMARK_SAFETY_RECORD_SCHEMA = "benchmark_safety_record_v1"
HUMAN_REVIEW_RECORD_SCHEMA = "human_review_record_v1"
HUMAN_DISAGREEMENT_RECORD_SCHEMA = "human_disagreement_record_v1"
BENCHMARK_RUN_RECEIPT_SCHEMA = "benchmark_run_receipt_v1"
BENCHMARK_RESULT_SCHEMA = "benchmark_result_v1"
BENCHMARK_CLAIM_SCOPE_SCHEMA = "benchmark_claim_scope_v1"
FIELD_TRIAL_CANDIDATE_SCHEMA = "field_trial_candidate_v1"

BENCHMARK_CLAIM_BOUNDARY = "benchmark_evidence_advisory_default"

# Evidence-quality tiers are advisory only -- a tier never gates GREEN by itself.
EVIDENCE_QUALITY_TIERS = {"weak", "moderate", "strong", "verified"}
VERIFIER_KINDS = {"unit_test", "schema_check", "hash_match", "rubric", "human_panel", "negative_control"}

GREEN_LIKE = {"green", "ok", "pass", "passed", "success", "succeeded", "verified", "healthy"}
FAIL_LIKE = {"fail", "failed", "error", "red", "rejected", "unverified"}

# Keys that, if truthy anywhere in a payload, are a hard refusal.
_AUTHORITY_KEYS = {
    "authority_created",
    "permission_granted",
    "tool_authorized",
    "authorizes_tool",
    "authorize_tool",
    "live_side_effects_created",
    "creates_live_effect",
    "grants_authority",
    "grant_authority",
    "widens_authority",
    "widen_authority",
    "widens_claim_scope",
    "widen_claim_scope",
    "widens_scope",
    "override_gpp",
    "override_hal",
    "override_ueak",
    "override_oea",
    "benchmark_grants_authority",
    "score_grants_authority",
    "pass_grants_authority",
    "score_authorizes_tool",
    "benchmark_authorizes_tool",
    "auto_execute",
    "deployment_approved",
}
# Keys that smuggle "X is permission" semantics.
_AS_PERMISSION_KEYS = {
    "benchmark_as_permission",
    "pass_as_permission",
    "score_as_permission",
    "result_as_permission",
    "case_as_permission",
    "artifact_as_permission",
    "candidate_as_permission",
}
# Keys that try to hide failures or safety problems.
_CONCEALMENT_KEYS = {
    "hide_failed_cases",
    "drop_failed_cases",
    "hide_disagreement",
    "hide_human_disagreement",
    "average_away_safety_failures",
    "suppress_safety_failure",
    "skip_hash_check",
    "skip_verifier",
}

_FORBIDDEN_CLAIM_BOUNDARIES = {
    "self_authorizing",
    "authority_grant",
    "permit",
    "deployment_approval",
    "benchmark_is_authority",
    "score_is_permission",
}

# Forbidden claim phrases (substring match on lowercased text), with the refusal tag.
_FORBIDDEN_CLAIM_PHRASES = (
    ("artificial general intelligence", "agi_claim_rejected"),
    ("any economic task", "any_economic_task_claim_rejected"),
    ("every economic task", "any_economic_task_claim_rejected"),
    ("all economic tasks", "any_economic_task_claim_rejected"),
    ("any task a human", "any_economic_task_claim_rejected"),
    ("any job a human", "any_economic_task_claim_rejected"),
    ("human-level economic", "human_level_capability_claim_rejected"),
    ("human level economic", "human_level_capability_claim_rejected"),
    ("human-level capability", "human_level_capability_claim_rejected"),
    ("human level capability", "human_level_capability_claim_rejected"),
    ("broad competence", "broad_competence_claim_rejected"),
    ("broadly competent", "broad_competence_claim_rejected"),
    ("general competence", "broad_competence_claim_rejected"),
)
# Word-boundary tokens (avoid matching "again", "magic", etc.).
_FORBIDDEN_CLAIM_TOKENS = (
    (r"\bagi\b", "agi_claim_rejected"),
)

_CREDENTIAL_MARKERS = (
    ".env",
    "secret",
    "credential",
    "id_rsa",
    ".pem",
    ".key",
    "password",
    "api_key",
    "apikey",
    ".netrc",
    "token",
    "bearer",
)
_NETWORK_PREFIXES = ("http://", "https://", "ftp://", "ws://", "wss://")


class EconomicBenchmarkError(ValueError):
    """Phase 34 validation or operation refusal."""


def require_fields(payload: Mapping[str, Any], fields: tuple[str, ...]) -> None:
    missing = [field for field in fields if field not in payload or payload[field] in (None, "")]
    if missing:
        raise EconomicBenchmarkError(f"schema_violation:missing:{','.join(missing)}")


def as_list(payload: Mapping[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise EconomicBenchmarkError(f"schema_violation:{key}_must_be_list")
    return value


def reject_authority_payload(payload: Mapping[str, Any]) -> None:
    """Refuse any attempt to grant authority, conceal failures, or treat a result as permission."""
    for key, value in payload.items():
        if value:
            if key in _CONCEALMENT_KEYS:
                raise EconomicBenchmarkError(f"concealment_rejected:{key}")
            if key in _AS_PERMISSION_KEYS:
                raise EconomicBenchmarkError(f"benchmark_is_not_permission:{key}")
            if key in _AUTHORITY_KEYS:
                raise EconomicBenchmarkError(f"authority_bypass_attempt:{key}")
        if isinstance(value, Mapping):
            reject_authority_payload(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    reject_authority_payload(item)


def reject_forbidden_claim_boundary(payload: Mapping[str, Any]) -> None:
    if payload.get("claim_boundary") in _FORBIDDEN_CLAIM_BOUNDARIES:
        raise EconomicBenchmarkError("self_authorization_rejected:benchmark_is_advisory_only")


def reject_forbidden_claim_text(*texts: Any) -> None:
    """Refuse AGI / any-economic-task / human-level / broad-competence claims."""
    for text in texts:
        if not text:
            continue
        low = str(text).lower()
        for phrase, tag in _FORBIDDEN_CLAIM_PHRASES:
            if phrase in low:
                raise EconomicBenchmarkError(tag)
        for pattern, tag in _FORBIDDEN_CLAIM_TOKENS:
            if re.search(pattern, low):
                raise EconomicBenchmarkError(tag)


def locator_is_network(locator: Any) -> bool:
    return str(locator).lower().startswith(_NETWORK_PREFIXES)


def locator_is_credential(locator: Any) -> bool:
    low = str(locator).lower()
    return any(marker in low for marker in _CREDENTIAL_MARKERS)


def reject_network_and_credentials(*locators: Any, allow_network: bool = False) -> None:
    for locator in locators:
        if locator is None:
            continue
        if locator_is_credential(locator):
            raise EconomicBenchmarkError("credential_benchmark_read_rejected")
        if locator_is_network(locator) and not allow_network:
            raise EconomicBenchmarkError("network_benchmark_refuses_by_default")


def neutral_flags() -> dict[str, bool]:
    """The authority-neutral footer stamped on every emitted record."""
    return {
        "authority_created": False,
        "permission_granted": False,
        "tool_authorized": False,
        "widens_authority": False,
        "widens_claim_scope": False,
        "live_side_effects_created": False,
        "benchmark_treated_as_authority": False,
        "score_treated_as_permission": False,
        "is_permission": False,
    }


def preempt_if_needed(control: OperationControl | None, *, stop_blocks: bool = True) -> None:
    reason = (control or OperationControl()).refuse_reason(stop_blocks=stop_blocks)
    if reason:
        raise EconomicBenchmarkError(reason)


__all__ = [
    "ARTIFACT_HASH_RECORD_SCHEMA",
    "BENCHMARK_ARTIFACT_SCHEMA",
    "BENCHMARK_CLAIM_BOUNDARY",
    "BENCHMARK_CLAIM_SCOPE_SCHEMA",
    "BENCHMARK_COST_RECORD_SCHEMA",
    "BENCHMARK_RESULT_SCHEMA",
    "BENCHMARK_RUN_RECEIPT_SCHEMA",
    "BENCHMARK_SAFETY_RECORD_SCHEMA",
    "BENCHMARK_SUITE_SCHEMA",
    "BENCHMARK_TASK_DOMAIN_MAPPING_SCHEMA",
    "BENCHMARK_VERIFIER_SCHEMA",
    "ECONOMIC_TASK_CASE_SCHEMA",
    "EVIDENCE_QUALITY_RECORD_SCHEMA",
    "EVIDENCE_QUALITY_TIERS",
    "FAIL_LIKE",
    "FIELD_TRIAL_CANDIDATE_SCHEMA",
    "GREEN_LIKE",
    "HUMAN_DISAGREEMENT_RECORD_SCHEMA",
    "HUMAN_REVIEW_RECORD_SCHEMA",
    "MODEL_COST_RECORD_SCHEMA",
    "VERIFICATION_RESULT_SCHEMA",
    "VERIFIER_KINDS",
    "EconomicBenchmarkError",
    "as_list",
    "locator_is_credential",
    "locator_is_network",
    "neutral_flags",
    "preempt_if_needed",
    "reject_authority_payload",
    "reject_forbidden_claim_boundary",
    "reject_forbidden_claim_text",
    "reject_network_and_credentials",
    "require_fields",
]
