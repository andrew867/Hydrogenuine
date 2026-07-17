"""Explicit science-mode → subagent-role mapping.

Never derive roles from string splitting. Every mode must map to a
registered role. Validation fails loudly at preflight, not mid-cycle.
"""

from __future__ import annotations

from dataclasses import dataclass, field


SCIENCE_MODE_TO_SUBAGENT_ROLE = {
    "build_the_case": "bridge_theory_worker",
    "disprove_the_case": "falsification_worker",
    "assume_real": "bridge_theory_worker",
    "assume_false": "boring_explanation_worker",
    "boring_explanation_first": "boring_explanation_worker",
    "units_and_math_audit": "units_math_audit_worker",
    "mechanism_builder": "bridge_theory_worker",
    "falsification_design": "falsification_worker",
    "source_discovery": "seed_ranker",
    "public_safe_explainer": "public_safe_explainer_worker",
    "adversarial_peer_review": "proof_auditor_worker",
    "synthesis_after_opposition": "bridge_theory_worker",
}


@dataclass
class RoleMapValidationResult:
    valid: bool = True
    missing_science_modes: list[str] = field(default_factory=list)
    unknown_roles: list[str] = field(default_factory=list)
    registered_roles: set[str] = field(default_factory=set)
    mapped_roles: set[str] = field(default_factory=set)


def resolve_subagent_role(science_mode: str) -> str | None:
    return SCIENCE_MODE_TO_SUBAGENT_ROLE.get(science_mode)


def validate_role_mapping(
    registered_roles: set[str], science_modes: set[str],
) -> RoleMapValidationResult:
    result = RoleMapValidationResult(
        registered_roles=set(registered_roles),
        mapped_roles=set(SCIENCE_MODE_TO_SUBAGENT_ROLE.values()),
    )
    for mode in science_modes:
        if mode not in SCIENCE_MODE_TO_SUBAGENT_ROLE:
            result.missing_science_modes.append(mode)
            result.valid = False
    for role in SCIENCE_MODE_TO_SUBAGENT_ROLE.values():
        if role not in registered_roles:
            result.unknown_roles.append(role)
            result.valid = False
    return result
