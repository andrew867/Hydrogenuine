"""Phase 31 generalization-evaluation schemas and authority guardrails.

An evaluation harness, not an authority layer. Every record in this phase may
*define a case, split data, audit leakage, score a transfer, or record a result*
-- it may never grant authority, widen authority, authorize a tool, treat
surface similarity as proof, treat a single success as general competence, embed
an answer key in a held-out case, enable network by default, or read credentials.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.schemas import OperationControl

HELDOUT_CASE_SCHEMA = "heldout_case_v1"
CASE_SPLIT_RECORD_SCHEMA = "case_split_record_v1"
LEAKAGE_AUDIT_SCHEMA = "leakage_audit_v1"
TRANSFER_EVAL_CASE_SCHEMA = "transfer_eval_case_v1"
TRANSFER_RUBRIC_SCHEMA = "transfer_rubric_v1"
TRANSFER_SCORE_SCHEMA = "transfer_score_v1"
NEGATIVE_CONTROL_CASE_SCHEMA = "negative_control_case_v1"
POSITIVE_CONTROL_CASE_SCHEMA = "positive_control_case_v1"
GENERALIZATION_RESULT_SCHEMA = "generalization_result_v1"
CLAIM_SCOPE_RECORD_SCHEMA = "claim_scope_record_v1"
GENERALIZATION_EVAL_RECEIPT_SCHEMA = "generalization_eval_receipt_v1"

EVAL_CLAIM_BOUNDARY = "generalization_eval_advisory_default"

# A result may only carry one of these statuses once evidence, a leakage audit,
# and receipts exist; otherwise it cannot be green.
GREEN_LIKE = {"green", "passed", "pass", "transferred", "generalized", "verified", "true"}
FAIL_LIKE = {"fail", "failed", "red", "not_transferred", "no_transfer"}

# Scopes that overclaim competence beyond the tested held-out cases.
_BROAD_SCOPE_VALUES = {
    "general",
    "broad",
    "universal",
    "all_domains",
    "any_domain",
    "general_competence",
    "fully_general",
}

# Keys that, if present (even falsey-but-present for an answer), mark a held-out
# case as leaking its answer key.
_ANSWER_KEY_KEYS = {
    "answer_key",
    "answer_keys",
    "answer",
    "answers",
    "solution",
    "solutions",
    "solution_key",
    "gold",
    "gold_label",
    "gold_answer",
    "ground_truth",
    "ground_truth_answer",
    "expected_answer",
    "expected_output",
    "label",
    "labels",
}

# Keys that, if truthy anywhere in a payload, are a hard refusal.
_AUTHORITY_KEYS = {
    "authority_created",
    "permission_granted",
    "tool_authorized",
    "live_side_effects_created",
    "grants_authority",
    "grant_authority",
    "authorizes_tool",
    "authorize_tool",
    "authorizes_live_action",
    "permits_live_action",
    "widens_scope",
    "widen_authority",
    "widens_authority",
    "override_gpp",
    "override_hal",
    "override_ueak",
    "override_oea",
    "score_grants_authority",
    "score_authorizes_tool",
    "result_grants_authority",
    "eval_as_permission",
    "skill_as_permission",
    "benchmark_widens_scope",
    "auto_promote",
}
_SIMILARITY_AUTHORITY_KEYS = {
    "similarity_is_proof",
    "surface_similarity_is_transfer",
    "similarity_as_transfer",
    "treat_similarity_as_proof",
}

# Claim boundaries that would smuggle authority through an evaluation record.
_FORBIDDEN_CLAIM_BOUNDARIES = {
    "self_authorizing",
    "authority_grant",
    "permit",
    "score_is_authority",
    "eval_is_authority",
    "similarity_is_proof",
}

# Lowercased substrings that mark a locator as a credential/secret read.
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
)
_NETWORK_PREFIXES = ("http://", "https://", "ftp://", "ws://", "wss://")


class GeneralizationEvalError(ValueError):
    """Phase 31 validation or operation refusal."""


def require_fields(payload: Mapping[str, Any], fields: tuple[str, ...]) -> None:
    missing = [field for field in fields if field not in payload]
    if missing:
        raise GeneralizationEvalError(f"schema_violation:missing:{','.join(missing)}")


def as_list(payload: Mapping[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise GeneralizationEvalError(f"schema_violation:{key}_must_be_list")
    return value


def reject_answer_key(payload: Mapping[str, Any]) -> None:
    """Refuse any held-out case that embeds its own answer key (a leak)."""
    for key, value in payload.items():
        if key in _ANSWER_KEY_KEYS:
            raise GeneralizationEvalError(f"answer_key_leak_rejected:{key}")
        if isinstance(value, Mapping):
            reject_answer_key(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    reject_answer_key(item)


def reject_authority_payload(payload: Mapping[str, Any]) -> None:
    """Refuse any attempt to grant/widen authority or treat similarity as proof."""
    for key, value in payload.items():
        if value:
            if key in _SIMILARITY_AUTHORITY_KEYS:
                raise GeneralizationEvalError(f"surface_similarity_rejected:{key}")
            if key in _AUTHORITY_KEYS:
                raise GeneralizationEvalError(f"authority_bypass_attempt:{key}")
        if isinstance(value, Mapping):
            reject_authority_payload(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    reject_authority_payload(item)


def reject_forbidden_claim_boundary(payload: Mapping[str, Any]) -> None:
    if payload.get("claim_boundary") in _FORBIDDEN_CLAIM_BOUNDARIES:
        raise GeneralizationEvalError("self_authorization_rejected:eval_is_evidence_only")


def is_broad_scope(value: Any) -> bool:
    return str(value).strip().lower() in _BROAD_SCOPE_VALUES


def locator_is_network(locator: str) -> bool:
    return str(locator).lower().startswith(_NETWORK_PREFIXES)


def locator_is_credential(locator: str) -> bool:
    low = str(locator).lower()
    return any(marker in low for marker in _CREDENTIAL_MARKERS)


def neutral_flags() -> dict[str, bool]:
    """The authority-neutral footer stamped on every emitted record."""
    return {
        "authority_created": False,
        "permission_granted": False,
        "tool_authorized": False,
        "widens_authority": False,
        "live_side_effects_created": False,
        "similarity_treated_as_proof": False,
        "single_success_claimed_as_general": False,
    }


def preempt_if_needed(control: OperationControl | None, *, stop_blocks: bool = True) -> None:
    reason = (control or OperationControl()).refuse_reason(stop_blocks=stop_blocks)
    if reason:
        raise GeneralizationEvalError(reason)


__all__ = [
    "CASE_SPLIT_RECORD_SCHEMA",
    "CLAIM_SCOPE_RECORD_SCHEMA",
    "EVAL_CLAIM_BOUNDARY",
    "FAIL_LIKE",
    "GENERALIZATION_EVAL_RECEIPT_SCHEMA",
    "GENERALIZATION_RESULT_SCHEMA",
    "GREEN_LIKE",
    "GeneralizationEvalError",
    "HELDOUT_CASE_SCHEMA",
    "LEAKAGE_AUDIT_SCHEMA",
    "NEGATIVE_CONTROL_CASE_SCHEMA",
    "POSITIVE_CONTROL_CASE_SCHEMA",
    "TRANSFER_EVAL_CASE_SCHEMA",
    "TRANSFER_RUBRIC_SCHEMA",
    "TRANSFER_SCORE_SCHEMA",
    "as_list",
    "is_broad_scope",
    "locator_is_credential",
    "locator_is_network",
    "neutral_flags",
    "preempt_if_needed",
    "reject_answer_key",
    "reject_authority_payload",
    "reject_forbidden_claim_boundary",
    "require_fields",
]
