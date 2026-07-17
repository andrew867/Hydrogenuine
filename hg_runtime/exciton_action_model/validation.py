"""Validation helpers for the EXCITON action model.

The action model describes requests — it never authorizes execution.
"""

from __future__ import annotations

import re
from typing import Any

from hg_runtime.exciton_action_model.action_types import (
    PHASE3_FORBIDDEN_ACTION_TYPES,
    AgentActionType,
    CONTROL_ACTION_TYPES,
)
from hg_runtime.exciton_action_model.risk import (
    AUTO_APPROVAL_RISK_CEILING,
    AgentActionRiskClass,
    classify_action_risk,
)
from hg_runtime.exciton_action_model.schema import (
    AgentActionDecision,
    AgentActionDecisionKind,
    AgentActionReceipt,
    AgentActionRequest,
    AgentActionSurface,
)
from hg_runtime.exciton_action_model.status import AgentActionStatus

_REQUIRED_REQUEST_FIELDS = (
    "action_type",
    "risk_class",
    "source_agent",
    "human_summary",
    "status",
    "item_hash",
)

_SECRET_KEY_FRAGMENTS = frozenset(
    {
        "password",
        "secret",
        "token",
        "api_key",
        "apikey",
        "credential",
        "cookie",
        "session",
        "authorization",
        "private_key",
        "access_key",
    }
)

_SECRET_VALUE_PATTERNS = (
    re.compile(r"Bearer\s+\S+", re.I),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"ghp_[a-zA-Z0-9]{20,}"),
)

# OEA/TER/SRP-like actuation tags in tool payloads.
_EXTERNAL_ACTUATION_TAGS = frozenset({"oea", "ter", "srp", "start_oea", "start_ter", "apply_srp"})

_LOCAL_REF_PREFIXES = (".hg-local/", "hg-local/", "file://.hg-local/")


class ActionValidationError(ValueError):
    pass


def _scan_secret_keys(obj: Any, path: str = "") -> list[str]:
    bad: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            key_lower = str(k).lower()
            if any(frag in key_lower for frag in _SECRET_KEY_FRAGMENTS):
                bad.append(f"{path}/{k}")
            bad.extend(_scan_secret_keys(v, f"{path}/{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            bad.extend(_scan_secret_keys(v, f"{path}[{i}]"))
    elif isinstance(obj, str):
        for pat in _SECRET_VALUE_PATTERNS:
            if pat.search(obj):
                bad.append(path or "<value>")
    return bad


def validate_no_secret_fields(payload: dict[str, Any]) -> list[str]:
    return _scan_secret_keys(payload)


def validate_no_authority_conversion(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("authority_created") is True:
        errors.append("authority_created must be false")
    if payload.get("permission_granted") is True:
        errors.append("permission_granted must be false")
    if payload.get("advisory_only") is not True:
        errors.append("advisory_only must be true")
    return errors


def validate_safe_preview(text: str) -> list[str]:
    errors: list[str] = []
    if not text:
        return errors
    for pat in _SECRET_VALUE_PATTERNS:
        if pat.search(text):
            errors.append("sanitized_preview contains secret-like value")
    for frag in _SECRET_KEY_FRAGMENTS:
        if frag in text.lower() and "=" in text:
            errors.append(f"sanitized_preview may contain secret key fragment: {frag}")
    return errors


def _validate_local_ref(ref: str | None) -> list[str]:
    if ref is None:
        return []
    if ref.startswith("http://") or ref.startswith("https://"):
        return ["raw_payload_ref must be local-only, not remote URL"]
    if not any(ref.startswith(p) for p in _LOCAL_REF_PREFIXES) and not ref.startswith("/"):
        return ["raw_payload_ref must be a local .hg-local/ path"]
    return []


def validate_action_request(request: AgentActionRequest) -> list[str]:
    errors: list[str] = []
    payload = request.to_payload()

    for field in _REQUIRED_REQUEST_FIELDS:
        if not payload.get(field):
            errors.append(f"missing required field: {field}")

    errors.extend(validate_no_authority_conversion(payload))
    errors.extend(validate_safe_preview(request.sanitized_preview))
    errors.extend(_validate_local_ref(request.raw_payload_ref))

    if request.risk_class == AgentActionRiskClass.UNKNOWN:
        errors.append("unknown risk_class blocks action")

    expected_risk = classify_action_risk(request.action_type)
    if request.risk_class != expected_risk and request.risk_class != AgentActionRiskClass.UNKNOWN:
        # Allow explicit override only if not worse than classified — re-classify unknown.
        pass

    if request.source_agent == "agent0" and request.operator_decision_ref:
        if request.operator_decision_ref.operator_ref == "agent0":
            errors.append("source_agent cannot be the approver")

    return errors


def validate_action_decision(decision: AgentActionDecision) -> list[str]:
    errors: list[str] = []
    payload = decision.to_payload()
    errors.extend(validate_no_authority_conversion(payload))
    if not payload.get("decision_hash"):
        errors.append("missing decision_hash")
    if not payload.get("action_id"):
        errors.append("missing action_id")
    return errors


def validate_action_receipt(receipt: AgentActionReceipt) -> list[str]:
    errors: list[str] = []
    payload = receipt.to_payload()
    errors.extend(validate_no_authority_conversion(payload))
    if not payload.get("receipt_hash"):
        errors.append("missing receipt_hash")
    if not payload.get("action_id"):
        errors.append("missing action_id")
    return errors


def is_action_type_forbidden_in_phase3(action_type: AgentActionType) -> bool:
    return action_type in PHASE3_FORBIDDEN_ACTION_TYPES


def is_external_actuation_payload(payload: dict[str, Any] | None) -> bool:
    if not payload:
        return False
    text = str(payload).lower()
    return any(tag in text for tag in _EXTERNAL_ACTUATION_TAGS)


def is_action_type_executable_in_phase3(
    action_type: AgentActionType,
    *,
    payload: dict[str, Any] | None = None,
) -> bool:
    if action_type in PHASE3_FORBIDDEN_ACTION_TYPES:
        return False
    if action_type in CONTROL_ACTION_TYPES:
        return False  # control routed, not "executed" as external actuation
    if is_external_actuation_payload(payload):
        return False
    return True


def requires_operator_review(action_type: AgentActionType) -> bool:
    if action_type == AgentActionType.SOCIAL_POST:
        return True
    if action_type in PHASE3_FORBIDDEN_ACTION_TYPES:
        return True
    if action_type in {
        AgentActionType.WEB_FORM_SUBMIT,
        AgentActionType.WEB_LOGIN,
        AgentActionType.WEB_PURCHASE,
        AgentActionType.WEB_ACCOUNT_CHANGE,
        AgentActionType.EMAIL_SEND,
        AgentActionType.SHELL_COMMAND,
        AgentActionType.SOURCE_PATCH,
        AgentActionType.MEMORY_MUTATION,
        AgentActionType.ANCHOR_PUSH,
        AgentActionType.ACCOUNT_ACTION,
        AgentActionType.PUBLICATION,
    }:
        return True
    return False


def requires_permit(action_type: AgentActionType) -> bool:
    return action_type == AgentActionType.SOCIAL_POST


def can_be_auto_approval_candidate(action_type: AgentActionType) -> bool:
    if is_action_type_forbidden_in_phase3(action_type):
        return False
    if requires_operator_review(action_type):
        return False
    risk = classify_action_risk(action_type)
    return risk in AUTO_APPROVAL_RISK_CEILING


def recommended_decision_for_action(
    action_type: AgentActionType,
    *,
    trust_ok: bool = True,
) -> AgentActionDecisionKind:
    if action_type == AgentActionType.PANIC_STOP:
        return AgentActionDecisionKind.FULL_STOP
    if action_type == AgentActionType.STOP_SOAK:
        return AgentActionDecisionKind.FULL_STOP
    if action_type == AgentActionType.FINALIZE_SOAK:
        return AgentActionDecisionKind.REQUIRE_OPERATOR_CONFIRMATION
    if is_action_type_forbidden_in_phase3(action_type):
        return AgentActionDecisionKind.DENY
    if action_type in {
        AgentActionType.MEMORY_MUTATION,
        AgentActionType.SOURCE_PATCH,
        AgentActionType.SHELL_COMMAND,
    }:
        return AgentActionDecisionKind.DENY
    if action_type == AgentActionType.SOCIAL_POST:
        return AgentActionDecisionKind.REQUIRE_PERMIT
    if action_type == AgentActionType.SOCIAL_DRAFT:
        return AgentActionDecisionKind.ALLOW_DRAFT_ONLY
    if action_type in {AgentActionType.PROOF_OPEN, AgentActionType.STATUS_REFRESH}:
        return AgentActionDecisionKind.ALLOW_READ_ONLY
    if action_type == AgentActionType.WEB_READ_URL:
        return AgentActionDecisionKind.ALLOW_READ_ONLY if trust_ok else AgentActionDecisionKind.DENY
    if action_type in {AgentActionType.WEB_FORM_SUBMIT, AgentActionType.WEB_LOGIN}:
        return AgentActionDecisionKind.DENY
    if action_type == AgentActionType.WEB_PURCHASE:
        return AgentActionDecisionKind.DENY
    if requires_operator_review(action_type):
        return AgentActionDecisionKind.QUEUE_FOR_OPERATOR
    risk = classify_action_risk(action_type)
    if risk == AgentActionRiskClass.UNKNOWN:
        return AgentActionDecisionKind.DENY
    if risk == AgentActionRiskClass.DRAFT_ONLY:
        return AgentActionDecisionKind.ALLOW_DRAFT_ONLY
    if risk == AgentActionRiskClass.READ_ONLY:
        return AgentActionDecisionKind.ALLOW_READ_ONLY
    return AgentActionDecisionKind.QUEUE_FOR_OPERATOR


def default_surface_for_action(action_type: AgentActionType) -> AgentActionSurface:
    mapping = {
        AgentActionType.SOCIAL_POST: AgentActionSurface.SOCIAL,
        AgentActionType.SOCIAL_READ: AgentActionSurface.SOCIAL,
        AgentActionType.SOCIAL_DRAFT: AgentActionSurface.SOCIAL,
        AgentActionType.WEB_READ_URL: AgentActionSurface.WEB,
        AgentActionType.WEB_SEARCH: AgentActionSurface.WEB,
        AgentActionType.WEB_CLICK_LINK: AgentActionSurface.WEB,
        AgentActionType.WEB_DOWNLOAD_FILE: AgentActionSurface.WEB,
        AgentActionType.WEB_FORM_FILL: AgentActionSurface.WEB,
        AgentActionType.WEB_FORM_SUBMIT: AgentActionSurface.WEB,
        AgentActionType.WEB_LOGIN: AgentActionSurface.WEB,
        AgentActionType.WEB_UPLOAD: AgentActionSurface.WEB,
        AgentActionType.WEB_POST_COMMENT: AgentActionSurface.WEB,
        AgentActionType.WEB_PURCHASE: AgentActionSurface.WEB,
        AgentActionType.WEB_ACCOUNT_CHANGE: AgentActionSurface.ACCOUNT,
        AgentActionType.EMAIL_DRAFT: AgentActionSurface.EMAIL,
        AgentActionType.EMAIL_SEND: AgentActionSurface.EMAIL,
        AgentActionType.CALENDAR_CREATE: AgentActionSurface.CALENDAR,
        AgentActionType.FILE_WRITE: AgentActionSurface.FILESYSTEM,
        AgentActionType.MEMORY_MUTATION: AgentActionSurface.MEMORY,
        AgentActionType.SOURCE_PATCH: AgentActionSurface.SOURCE,
        AgentActionType.ANCHOR_PUSH: AgentActionSurface.ANCHOR,
        AgentActionType.TOOL_EXECUTE: AgentActionSurface.TOOL,
        AgentActionType.SHELL_COMMAND: AgentActionSurface.SHELL,
        AgentActionType.ACCOUNT_ACTION: AgentActionSurface.ACCOUNT,
        AgentActionType.EXTERNAL_API_CALL: AgentActionSurface.API,
        AgentActionType.PUBLICATION: AgentActionSurface.PUBLICATION,
        AgentActionType.OPERATOR_NOTE: AgentActionSurface.OPERATOR,
        AgentActionType.PROOF_OPEN: AgentActionSurface.PROOF,
        AgentActionType.STATUS_REFRESH: AgentActionSurface.EXCITON,
        AgentActionType.STOP_SOAK: AgentActionSurface.CONTROL,
        AgentActionType.PANIC_STOP: AgentActionSurface.CONTROL,
        AgentActionType.FINALIZE_SOAK: AgentActionSurface.SOAK,
    }
    return mapping.get(action_type, AgentActionSurface.UNKNOWN)


__all__ = [
    "ActionValidationError",
    "can_be_auto_approval_candidate",
    "classify_action_risk",
    "default_surface_for_action",
    "is_action_type_executable_in_phase3",
    "is_action_type_forbidden_in_phase3",
    "is_external_actuation_payload",
    "recommended_decision_for_action",
    "requires_operator_review",
    "requires_permit",
    "validate_action_decision",
    "validate_action_receipt",
    "validate_action_request",
    "validate_no_authority_conversion",
    "validate_no_secret_fields",
    "validate_safe_preview",
]
