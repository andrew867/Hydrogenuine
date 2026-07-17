"""CLIFT-02 / CAGI-67 containment and capability boundary domain logic."""

from __future__ import annotations

from hg_runtime.containment_capability_boundary.schemas import (
    CONTAINMENT_MODES,
    ContainmentBoundaryError,
    reject_containment_escape,
)


def validate_capability_declaration(decl: dict) -> list[str]:
    issues = []
    if not decl.get("capability_id"):
        issues.append("missing_capability_id")
    if not decl.get("name"):
        issues.append("missing_name")
    if decl.get("authorized"):
        issues.append("declaration_must_not_authorize")
    if decl.get("containment_mode") not in CONTAINMENT_MODES:
        issues.append("invalid_containment_mode")
    return issues


def validate_containment_mode(record: dict) -> list[str]:
    issues = []
    if record.get("mode") not in CONTAINMENT_MODES:
        issues.append("invalid_mode")
    if record.get("provider_enabled"):
        issues.append("provider_must_not_be_enabled")
    if record.get("network_enabled"):
        issues.append("network_must_not_be_enabled")
    if record.get("tool_authorized"):
        issues.append("tool_must_not_be_authorized")
    if record.get("hg_local_accessible"):
        issues.append("hg_local_must_not_be_accessible")
    return issues


def detect_escalation(payload: dict) -> bool:
    return bool(payload.get("capability_escalated"))


def quarantine_violation(violation: dict) -> dict:
    return {
        "quarantine_id": f"quar-{violation.get('capability_id', 'unknown')}",
        "violation": violation,
        "quarantined": True,
        "escalated_to_operator": True,
    }


def is_deployment_permission(record: dict) -> bool:
    return bool(record.get("deployment_permission") or record.get("deployment_permission_claimed"))
