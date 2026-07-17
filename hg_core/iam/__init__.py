"""
IAM — enterprise OIDC/RBAC (Phase 5) and local operator authority (CT-01).
"""

from .authority import (
    assert_registry_mutation_allowed,
    bind_authority,
    is_registered_human_actor,
    scope_for_plt_action,
    validate_operator_authority,
    verify_binding,
)
from .ingress import dual_checkpoint_admit, ueak_ingress_check, ueak_translation_check
from .oidc import (
    check_permission,
    get_roles_for_principal,
    load_oidc_config,
    load_rbac_config,
    record_privileged_access,
    resolve_approvers_for_action,
    validate_oidc_claims,
)
from .registry import load_registry, resolve_operator_id
from .types import AGENT_ZERO_ID, AuthorityBinding, AuthorityResult

__all__ = [
    "AGENT_ZERO_ID",
    "AuthorityBinding",
    "AuthorityResult",
    "assert_registry_mutation_allowed",
    "bind_authority",
    "dual_checkpoint_admit",
    "is_registered_human_actor",
    "load_registry",
    "resolve_operator_id",
    "scope_for_plt_action",
    "ueak_ingress_check",
    "ueak_translation_check",
    "validate_operator_authority",
    "verify_binding",
    "validate_oidc_claims",
    "get_roles_for_principal",
    "check_permission",
    "resolve_approvers_for_action",
    "load_oidc_config",
    "load_rbac_config",
    "record_privileged_access",
]
