"""Hydrogenuine role registry + legacy Keycloak role mapping.

`service` is a machine identity and can never approve as a human — enforced by
`can_approve_as_human`, not by convention.
"""
from __future__ import annotations

HG_ROLES = (
    "hg.viewer", "hg.operator", "hg.reviewer", "hg.approver",
    "hg.high_risk_approver", "hg.restricted_approver", "hg.breakglass",
    "hg.admin", "hg.config_admin", "hg.audit_viewer", "hg.workflow_designer",
    "hg.model_operator", "hg.memory_admin", "hg.embodied_operator",
    "hg.embodied_safety_officer", "hg.hardware_admin",
)

# Legacy realm roles → Hydrogenuine roles (mirrors realm.json composites).
LEGACY_ROLE_MAP: dict[str, tuple[str, ...]] = {
    "superadmin": ("hg.admin", "hg.config_admin", "hg.breakglass"),
    "tenant_admin": ("hg.admin", "hg.approver"),
    "operator": ("hg.operator", "hg.approver"),
    "viewer": ("hg.viewer",),
    "service": (),  # machine identity — maps to NO human approver role
}

HUMAN_APPROVER_ROLES = frozenset({
    "hg.approver", "hg.high_risk_approver", "hg.restricted_approver",
    "hg.breakglass", "hg.admin",
})


def map_roles(token_roles: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    """Expand legacy roles into hg.* roles; pass through hg.* roles verbatim."""
    out: list[str] = []
    for role in token_roles:
        if role.startswith("hg.") and role in HG_ROLES and role not in out:
            out.append(role)
        for mapped in LEGACY_ROLE_MAP.get(role, ()):
            if mapped not in out:
                out.append(mapped)
    return tuple(out)


def can_approve_as_human(token_roles: list[str] | tuple[str, ...]) -> bool:
    """Service principals can never approve, even with stray approver roles."""
    if "service" in token_roles:
        return False
    return bool(HUMAN_APPROVER_ROLES.intersection(map_roles(token_roles)))


__all__ = ["HG_ROLES", "HUMAN_APPROVER_ROLES", "LEGACY_ROLE_MAP",
           "can_approve_as_human", "map_roles"]
