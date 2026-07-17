"""Scope policy — no expansion, explicit platform/action/scope."""

from __future__ import annotations

from hg_runtime.external_write_authority.schema import ExternalActionType, PermitDenyReason


def scope_matches(permitted: str, requested: str) -> bool:
    return permitted.strip() == requested.strip()


def platform_matches(permitted: str, requested: str) -> bool:
    return permitted.strip().lower() == requested.strip().lower()


def action_matches(permitted: ExternalActionType | str, requested: ExternalActionType | str) -> bool:
    p = permitted.value if isinstance(permitted, ExternalActionType) else permitted
    r = requested.value if isinstance(requested, ExternalActionType) else requested
    return p == r


def validate_scope_no_expansion(
    *,
    candidate_scope: str,
    requested_scope: str,
    permitted_scope: str,
) -> list[PermitDenyReason]:
    reasons: list[PermitDenyReason] = []
    if not scope_matches(candidate_scope, requested_scope):
        reasons.append(PermitDenyReason.SCOPE_EXPANSION)
    if not scope_matches(permitted_scope, candidate_scope):
        reasons.append(PermitDenyReason.SCOPE_EXPANSION)
    return reasons
