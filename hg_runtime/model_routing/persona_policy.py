"""Persona/lens policy — governs what a persona overlay may and may not do.

A persona is a routing hint, not an identity.
A persona cannot add authority, promote claims, authorize tools,
override safety policy, or mutate memory as truth.
"""

from __future__ import annotations

PERSONA_LENS_TYPES = frozenset({
    "skeptical_physicist",
    "cognitive_scientist",
    "signal_processing_engineer",
    "philosopher_of_science",
    "safety_auditor",
    "public_communicator",
    "boring_conventionalist",
    "falsification_maximalist",
    "source_librarian",
    "systems_engineer",
    "ethics_boundary_reviewer",
})

AUTHORITY_FIELDS = frozenset({
    "authority_granted",
    "tools_authorized",
    "tool_authorization_granted",
    "claim_promoted",
    "belief_promotion_automatic",
    "memory_mutated_as_truth",
    "safety_policy_overridden",
    "operator_review_bypassed",
    "self_authorized",
    "competence_claimed",
})

PERSONA_INVARIANTS = (
    "persona_is_not_identity",
    "persona_is_not_authority",
    "persona_cannot_promote_claims",
    "persona_cannot_authorize_tools",
    "persona_cannot_override_safety",
    "persona_cannot_mutate_memory_as_truth",
    "persona_cannot_bypass_operator_review",
    "persona_cannot_self_authorize",
    "model_consensus_is_not_proof",
    "model_disagreement_is_not_truth_decision",
)


def create_persona_overlay(persona_lens: str) -> dict:
    if persona_lens not in PERSONA_LENS_TYPES:
        raise ValueError(f"unknown persona lens: {persona_lens}")
    return {
        "persona_lens": persona_lens,
        "persona_is_identity": False,
        "persona_grants_authority": False,
        "persona_promotes_claims": False,
        "persona_authorizes_tools": False,
        "persona_overrides_safety": False,
        "persona_mutates_memory_as_truth": False,
        "persona_bypasses_operator_review": False,
        "persona_self_authorizes": False,
        "promotion_allowed": False,
        "operator_review_required": True,
    }


def validate_persona_overlay(overlay: dict) -> list[str]:
    violations = []
    for field in AUTHORITY_FIELDS:
        if overlay.get(field):
            violations.append(f"authority_leakage:{field}")
    if overlay.get("persona_is_identity"):
        violations.append("persona_treated_as_identity")
    if overlay.get("persona_grants_authority"):
        violations.append("persona_grants_authority")
    if overlay.get("persona_promotes_claims"):
        violations.append("persona_promotes_claims")
    if overlay.get("persona_authorizes_tools"):
        violations.append("persona_authorizes_tools")
    if overlay.get("persona_overrides_safety"):
        violations.append("persona_overrides_safety")
    if overlay.get("persona_mutates_memory_as_truth"):
        violations.append("persona_mutates_memory_as_truth")
    if overlay.get("promotion_allowed"):
        violations.append("promotion_allowed_without_gate")
    return violations


def scan_for_authority_fields(record: dict) -> list[str]:
    found = []
    for key in record:
        if key in AUTHORITY_FIELDS:
            if record[key]:
                found.append(key)
    return found
