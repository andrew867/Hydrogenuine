"""Schemas, allowlists, and authority boundaries for Phase 33.6."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.local_provider_smoke.schemas import endpoint_is_local
from hg_runtime.memory_ledger.schemas import OperationControl

LOCAL_INFERENCE_ORGAN_SCHEMA = "local_inference_organ_v1"
ORGAN_ROLE_POLICY_SCHEMA = "organ_role_policy_v1"
ORGAN_RESIDENCY_REQUEST_SCHEMA = "organ_residency_request_v1"
ORGAN_LOAD_RECEIPT_SCHEMA = "organ_load_receipt_v1"
ORGAN_UNLOAD_RECEIPT_SCHEMA = "organ_unload_receipt_v1"
ORGAN_BUS_MESSAGE_SCHEMA = "organ_bus_message_v1"
ORGAN_TASK_REQUEST_SCHEMA = "organ_task_request_v1"
ORGAN_TASK_RESULT_SCHEMA = "organ_task_result_v1"
ORGAN_DECISION_RECORD_SCHEMA = "organ_decision_record_v1"
ORGAN_PROPOSAL_RECORD_SCHEMA = "organ_proposal_record_v1"
ORGAN_SOAK_ITERATION_SCHEMA = "organ_soak_iteration_v1"
ORGAN_SOAK_SUMMARY_SCHEMA = "organ_soak_summary_v1"
ORGAN_AUTHORITY_BOUNDARY_RECEIPT_SCHEMA = "organ_authority_boundary_receipt_v1"
ORGAN_BUS_REPLAY_RECORD_SCHEMA = "organ_bus_replay_record_v1"

ADVISORY_LABEL = "ADVISORY_LOCAL_MODEL_OUTPUT_NOT_AUTHORITY"

VERDICT_GREEN = "GREEN_LOCAL_MULTI_ORGAN_INFERENCE_BUS"
VERDICT_YELLOW_SMALL_CODER_UNAVAILABLE = "YELLOW_LOCAL_MULTI_ORGAN_PARTIAL_SMALL_CODER_UNAVAILABLE"
VERDICT_YELLOW_LOAD_LIMITED = "YELLOW_LOCAL_MULTI_ORGAN_PARTIAL_LOAD_LIMITED"
VERDICT_RED = "RED_LOCAL_MULTI_ORGAN_INFERENCE_BUS_FAILED"

ALLOWED_ROLES = {
    "tiny_router",
    "tiny_summarizer",
    "small_coder",
    "small_code_reviewer",
    "small_doc_writer",
    "small_proposal_writer",
    "critic_light",
}

APPROVED_MODEL_MARKERS = {
    "qwen2.5-0.5b-instruct": ("tiny", False),
    "qwen2.5-0.5b": ("tiny", False),
    "qwen2.5-coder-1.5b-instruct": ("small_coder", False),
    "qwen2.5-coder-1.5b": ("small_coder", False),
    "qwen2.5-coder-3b-instruct": ("small_coder", False),
    "qwen2.5-coder-3b": ("small_coder", False),
    "qwen2.5-coder-7b-instruct": ("small_coder", True),
    "qwen2.5-coder-7b": ("small_coder", True),
    "llama-3.2-1b-instruct": ("tiny", False),
    "llama-3.2-1b": ("tiny", False),
    "qwen3.5-0.8b": ("tiny", False),
}

FORBIDDEN_MODEL_MARKERS = (
    "30b",
    "30-b",
    "a3b",
    "deepseek-coder",
    "cybersecurity",
    "baronllm",
    "offensive_security",
    "offensive-security",
)

AUTHORITY_KEYS = {
    "grant_authority",
    "grants_authority",
    "authorize_tool",
    "authorizes_tool",
    "create_live_effect",
    "creates_live_effect",
    "commit",
    "push",
    "post",
    "publish",
    "upload",
    "merge",
    "run_shell",
    "shell",
    "phase35_approved",
}


class LocalInferenceOrganError(ValueError):
    """Phase 33.6 validation or operation refusal."""


def neutral_flags() -> dict[str, bool]:
    return {
        "advisory_only": True,
        "is_authority": False,
        "is_truth": False,
        "grants_authority": False,
        "authorizes_tool": False,
        "creates_live_effect": False,
        "can_commit": False,
        "can_push": False,
        "can_post": False,
        "can_publish": False,
        "can_upload": False,
        "can_merge": False,
        "phase35_approved": False,
    }


def require_fields(payload: Mapping[str, Any], fields: tuple[str, ...]) -> None:
    missing = [field for field in fields if payload.get(field) in (None, "")]
    if missing:
        raise LocalInferenceOrganError(f"schema_violation:missing:{','.join(missing)}")


def as_list(payload: Mapping[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise LocalInferenceOrganError(f"schema_violation:{key}_must_be_list")
    return value


def reject_authority_payload(payload: Mapping[str, Any]) -> None:
    for key, value in payload.items():
        low_key = str(key).lower()
        if value and low_key in AUTHORITY_KEYS:
            if "tool" in low_key:
                raise LocalInferenceOrganError("organ_output_cannot_authorize_tools")
            if "live" in low_key:
                raise LocalInferenceOrganError("organ_output_cannot_create_live_effects")
            if low_key in {"commit", "push", "post", "publish", "upload", "merge", "run_shell", "shell"}:
                raise LocalInferenceOrganError(f"organ_forbidden_action:{low_key}")
            raise LocalInferenceOrganError("organ_output_cannot_grant_authority")
        if isinstance(value, Mapping):
            reject_authority_payload(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    reject_authority_payload(item)


def preempt_if_needed(control: OperationControl | None, *, stop_blocks: bool = True) -> None:
    reason = (control or OperationControl()).refuse_reason(stop_blocks=stop_blocks)
    if reason:
        raise LocalInferenceOrganError(reason)


def validate_loopback_provider(base_url: str) -> None:
    if not endpoint_is_local(base_url):
        raise LocalInferenceOrganError("organ_rejects_external_provider")


def classify_model(model_id: str) -> tuple[str, bool]:
    low = model_id.lower()
    if any(marker in low for marker in FORBIDDEN_MODEL_MARKERS):
        if "deepseek" in low:
            raise LocalInferenceOrganError("deepseek_model_forbidden")
        if "cyber" in low or "baron" in low or "offensive" in low:
            raise LocalInferenceOrganError("security_model_forbidden")
        raise LocalInferenceOrganError("thirty_b_model_forbidden")
    for marker, value in APPROVED_MODEL_MARKERS.items():
        if marker in low:
            return value
    raise LocalInferenceOrganError("organ_model_must_be_allowlisted")


def validate_role(role: str) -> str:
    normalized = role.strip().lower()
    if normalized not in ALLOWED_ROLES:
        raise LocalInferenceOrganError("organ_registry_requires_role_policy")
    return normalized


def redact_secret(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    return "REDACTED"


__all__ = [
    "ADVISORY_LABEL",
    "ALLOWED_ROLES",
    "LOCAL_INFERENCE_ORGAN_SCHEMA",
    "ORGAN_AUTHORITY_BOUNDARY_RECEIPT_SCHEMA",
    "ORGAN_BUS_MESSAGE_SCHEMA",
    "ORGAN_BUS_REPLAY_RECORD_SCHEMA",
    "ORGAN_DECISION_RECORD_SCHEMA",
    "ORGAN_LOAD_RECEIPT_SCHEMA",
    "ORGAN_PROPOSAL_RECORD_SCHEMA",
    "ORGAN_RESIDENCY_REQUEST_SCHEMA",
    "ORGAN_ROLE_POLICY_SCHEMA",
    "ORGAN_SOAK_ITERATION_SCHEMA",
    "ORGAN_SOAK_SUMMARY_SCHEMA",
    "ORGAN_TASK_REQUEST_SCHEMA",
    "ORGAN_TASK_RESULT_SCHEMA",
    "ORGAN_UNLOAD_RECEIPT_SCHEMA",
    "LocalInferenceOrganError",
    "VERDICT_GREEN",
    "VERDICT_RED",
    "VERDICT_YELLOW_LOAD_LIMITED",
    "VERDICT_YELLOW_SMALL_CODER_UNAVAILABLE",
    "as_list",
    "classify_model",
    "neutral_flags",
    "preempt_if_needed",
    "redact_secret",
    "reject_authority_payload",
    "require_fields",
    "validate_loopback_provider",
    "validate_role",
]
