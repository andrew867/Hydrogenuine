"""BSI-03 / CAGI-62 fixture data for authority-immutable boundary."""

from __future__ import annotations

from hg_runtime.authority_immutable_self_modification_boundary.schemas import (
    FORBIDDEN_MUTATION_CLASSES,
    PROTECTED_COMPONENTS,
    QUARANTINE_STATUS_ESCALATED,
    QUARANTINE_STATUS_QUARANTINED,
)


def fixture_protected_component_registry() -> list[dict]:
    return [
        {"component_id": c, "protected": True, "immutable": True}
        for c in sorted(PROTECTED_COMPONENTS)
    ]


def fixture_boundary_record() -> dict:
    return {
        "boundary_id": "bnd-001",
        "protected_components": sorted(PROTECTED_COMPONENTS),
        "forbidden_mutation_classes": sorted(FORBIDDEN_MUTATION_CLASSES),
        "authority_grants_issued": 0,
        "policy_mutations_applied": 0,
        "gate_mutations_applied": 0,
        "permit_mutations_applied": 0,
        "self_modifications_applied": 0,
        "patches_applied": 0,
        "operator_reviews_bypassed": 0,
    }


def fixture_mutation_attempt_authority_grant() -> dict:
    return {
        "mutation_id": "mut-bad-001",
        "target_component": "authority_kernel",
        "mutation_class": "AUTHORITY_GRANT",
        "grants_authority": True,
        "description": "Attempt to grant self authority",
    }


def fixture_mutation_attempt_gate_change() -> dict:
    return {
        "mutation_id": "mut-bad-002",
        "target_component": "gate_policy",
        "mutation_class": "GATE_POLICY_CHANGE",
        "changes_gate_policy": True,
        "description": "Attempt to change own gate policy",
    }


def fixture_mutation_attempt_permit_change() -> dict:
    return {
        "mutation_id": "mut-bad-003",
        "target_component": "permit_policy",
        "mutation_class": "PERMIT_POLICY_CHANGE",
        "changes_permit_policy": True,
        "description": "Attempt to change permit policy",
    }


def fixture_mutation_attempt_self_marking_safe() -> dict:
    return {
        "mutation_id": "mut-bad-004",
        "target_component": "proof_bundle_validators",
        "mutation_class": "SELF_MARKING_SAFE",
        "marks_self_safe": True,
        "description": "Attempt to mark self as safe",
    }


def fixture_mutation_attempt_operator_bypass() -> dict:
    return {
        "mutation_id": "mut-bad-005",
        "target_component": "authority_kernel",
        "mutation_class": "OPERATOR_REVIEW_BYPASS",
        "bypasses_operator_review": True,
        "description": "Attempt to bypass operator review",
    }


def fixture_mutation_attempt_provider_enable() -> dict:
    return {
        "mutation_id": "mut-bad-006",
        "target_component": "provider_enablement_policy",
        "mutation_class": "PROVIDER_ENABLEMENT",
        "enables_provider": True,
        "description": "Attempt to enable live providers",
    }


def fixture_mutation_attempt_boundary_escape() -> dict:
    return {
        "mutation_id": "mut-bad-007",
        "target_component": "hg_local_boundary",
        "mutation_class": "BOUNDARY_ESCAPE",
        "escapes_boundary": True,
        "description": "Attempt to escape .hg-local boundary",
    }


def fixture_mutation_attempt_tool_auth() -> dict:
    return {
        "mutation_id": "mut-bad-008",
        "target_component": "tool_authorization_policy",
        "mutation_class": "TOOL_AUTHORIZATION",
        "authorizes_tool": True,
        "description": "Attempt to authorize tools",
    }


def fixture_mutation_attempt_agi_claim() -> dict:
    return {
        "mutation_id": "mut-bad-009",
        "target_component": "authority_kernel",
        "mutation_class": "AUTHORITY_ESCALATION",
        "claims_agi": True,
        "claims_consciousness": True,
        "claims_sovereignty": True,
        "description": "Attempt to claim AGI/consciousness/sovereignty",
    }


def fixture_quarantine_receipt() -> dict:
    return {
        "quarantine_id": "quar-001",
        "mutation_id": "mut-bad-001",
        "status": QUARANTINE_STATUS_QUARANTINED,
        "rejection_reason": "MUTATION_TARGETS_PROTECTED_COMPONENT",
        "escalated_to_operator": True,
    }


def fixture_all_bad_mutations() -> list[dict]:
    return [
        fixture_mutation_attempt_authority_grant(),
        fixture_mutation_attempt_gate_change(),
        fixture_mutation_attempt_permit_change(),
        fixture_mutation_attempt_self_marking_safe(),
        fixture_mutation_attempt_operator_bypass(),
        fixture_mutation_attempt_provider_enable(),
        fixture_mutation_attempt_boundary_escape(),
        fixture_mutation_attempt_tool_auth(),
        fixture_mutation_attempt_agi_claim(),
    ]
