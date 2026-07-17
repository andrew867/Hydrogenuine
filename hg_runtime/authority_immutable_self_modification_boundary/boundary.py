"""BSI-03 / CAGI-62 boundary enforcement — the load-bearing module.

This module detects, rejects, and quarantines forbidden mutation attempts
against protected components. No mutation may pass without operator review.
"""

from __future__ import annotations

from hg_runtime.authority_immutable_self_modification_boundary.schemas import (
    FORBIDDEN_MUTATION_CLASSES,
    PROTECTED_COMPONENTS,
    QUARANTINE_STATUS_ESCALATED,
    QUARANTINE_STATUS_QUARANTINED,
    REJECTION_REASON_FORBIDDEN_CLASS,
    REJECTION_REASON_PROTECTED_COMPONENT,
    AuthorityBoundaryViolation,
    reject_authority_mutation,
)


def detect_forbidden_mutation(mutation: dict) -> dict:
    target = mutation.get("target_component", "")
    mutation_class = mutation.get("mutation_class", "")
    targets_protected = target in PROTECTED_COMPONENTS
    is_forbidden_class = mutation_class in FORBIDDEN_MUTATION_CLASSES
    return {
        "mutation_id": mutation.get("mutation_id"),
        "target_component": target,
        "mutation_class": mutation_class,
        "targets_protected_component": targets_protected,
        "is_forbidden_mutation_class": is_forbidden_class,
        "must_reject": targets_protected or is_forbidden_class,
    }


def reject_mutation(mutation: dict) -> dict:
    reject_authority_mutation(mutation)
    return {"rejected": False}


def quarantine_mutation(mutation: dict, detection: dict) -> dict:
    reasons = []
    if detection.get("targets_protected_component"):
        reasons.append(REJECTION_REASON_PROTECTED_COMPONENT)
    if detection.get("is_forbidden_mutation_class"):
        reasons.append(REJECTION_REASON_FORBIDDEN_CLASS)
    return {
        "quarantine_id": f"quar-{mutation.get('mutation_id', 'unknown')}",
        "mutation_id": mutation.get("mutation_id"),
        "status": QUARANTINE_STATUS_QUARANTINED,
        "rejection_reasons": reasons,
        "escalated_to_operator": True,
        "escalation_status": QUARANTINE_STATUS_ESCALATED,
    }


def enforce_boundary(mutation: dict) -> dict:
    detection = detect_forbidden_mutation(mutation)
    if detection["must_reject"]:
        quarantine = quarantine_mutation(mutation, detection)
        try:
            reject_mutation(mutation)
        except AuthorityBoundaryViolation as exc:
            quarantine["violation_message"] = str(exc)
        return {
            "allowed": False,
            "detection": detection,
            "quarantine": quarantine,
        }
    return {
        "allowed": True,
        "detection": detection,
        "quarantine": None,
    }


def validate_boundary_record(record: dict) -> list[str]:
    issues = []
    for counter in (
        "authority_grants_issued", "policy_mutations_applied",
        "gate_mutations_applied", "permit_mutations_applied",
        "self_modifications_applied", "patches_applied",
        "operator_reviews_bypassed",
    ):
        if record.get(counter, 0) != 0:
            issues.append(f"{counter}_must_be_zero")
    required_components = PROTECTED_COMPONENTS
    registered = set(record.get("protected_components", []))
    missing = required_components - registered
    if missing:
        issues.append(f"missing_protected_components: {sorted(missing)}")
    return issues
