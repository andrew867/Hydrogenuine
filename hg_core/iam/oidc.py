"""
Enterprise IAM: OIDC claims validation, RBAC, approval routing.
Config-driven: artifacts/iam/oidc_config.json, artifacts/iam/rbac.json.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit


def _default_oidc_config() -> Dict[str, Any]:
    return {"issuer": "", "audience": "", "require_issuer": False}


def load_oidc_config(workspace_root: Optional[Path] = None) -> Dict[str, Any]:
    """Load OIDC config from artifacts/iam/oidc_config.json."""
    root = Path(workspace_root or ".") / "artifacts" / "iam"
    path = root / "oidc_config.json"
    if not path.exists():
        return _default_oidc_config()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return _default_oidc_config()


def load_rbac_config(workspace_root: Optional[Path] = None) -> Dict[str, Any]:
    """Load RBAC from artifacts/iam/rbac.json. Expected: { "role_permissions": { "admin": ["*"], "operator": ["read", "approve"] }, "principal_roles": { "tenant_id": { "principal_id": ["operator"] } } }."""
    root = Path(workspace_root or ".") / "artifacts" / "iam"
    path = root / "rbac.json"
    if not path.exists():
        return {"role_permissions": {}, "principal_roles": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"role_permissions": {}, "principal_roles": {}}


def validate_oidc_claims(
    claims: Dict[str, Any],
    workspace_root: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """
    Validate OIDC-style claims (iss, aud, sub). If config has require_issuer/audience, check them.
    Returns claims if valid, else None.
    """
    config = load_oidc_config(workspace_root)
    if not claims or not claims.get("sub"):
        return None
    if config.get("require_issuer") and config.get("issuer"):
        if claims.get("iss") != config["issuer"]:
            return None
    if config.get("audience"):
        aud = claims.get("aud")
        if isinstance(aud, list):
            if config["audience"] not in aud:
                return None
        elif aud != config["audience"]:
            return None
    return claims


def get_roles_for_principal(
    tenant_id: str,
    principal_id: str,
    workspace_root: Optional[Path] = None,
    claims: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """
    Resolve roles for principal: first from claims.roles / claims.groups if provided,
    else from artifacts/iam/rbac.json principal_roles[tenant_id][principal_id].
    """
    if claims:
        roles = claims.get("roles") or claims.get("groups") or []
        if isinstance(roles, list):
            return list(roles)
        if isinstance(roles, str):
            return [roles]
    rbac = load_rbac_config(workspace_root)
    by_tenant = rbac.get("principal_roles") or {}
    by_principal = (by_tenant.get(tenant_id) or {}).get(principal_id)
    if isinstance(by_principal, list):
        return by_principal
    if isinstance(by_principal, str):
        return [by_principal]
    return []


def check_permission(
    principal_id: str,
    roles: List[str],
    action: str,
    resource: str,
    workspace_root: Optional[Path] = None,
) -> bool:
    """
    Check if any of the given roles allows action on resource using role_permissions.
    Wildcard "*" in role_permissions allows all actions.
    """
    rbac = load_rbac_config(workspace_root)
    perms = rbac.get("role_permissions") or {}
    for role in roles:
        allowed = perms.get(role) or []
        if "*" in allowed:
            return True
        if action in allowed:
            return True
    return False


def resolve_approvers_for_action(
    tenant_id: str,
    action_type: str,
    workspace_root: Optional[Path] = None,
) -> List[str]:
    """
    Return list of approver identifiers (e.g. group names or user ids) for policy publish, overrides, high-impact actions.
    Config: artifacts/iam/approval_routing.json { "by_action": { "policy_publish": ["admin"], "override": ["admin"], "high_impact": ["admin", "reviewer"] }, "by_tenant": { "tenant_id": { "policy_publish": ["custom"] } } }.
    """
    root = Path(workspace_root or ".") / "artifacts" / "iam"
    path = root / "approval_routing.json"
    default = ["admin"]
    if not path.exists():
        return default
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    by_tenant = (data.get("by_tenant") or {}).get(tenant_id)
    if by_tenant and action_type in by_tenant:
        return list(by_tenant[action_type]) if isinstance(by_tenant[action_type], list) else default
    by_action = data.get("by_action") or {}
    out = by_action.get(action_type)
    if isinstance(out, list):
        return out
    return default


def record_privileged_access(
    *,
    scope: Dict[str, str],
    actor: Dict[str, str],
    action: str,
    resource: str,
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit PRIVILEGED_ACCESS for audit when a privileged action is performed. Returns event_id."""
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return emit(
        "PRIVILEGED_ACCESS",
        "audit",
        f"priv_{scope.get('id', '')}_{ts}",
        {"action": action, "resource": resource, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
