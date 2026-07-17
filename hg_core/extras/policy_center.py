"""
Policy center: unified policy registry, POLICY_PUBLISHED, POLICY_APPLIED, POLICY_OVERRIDE_APPLIED.
Active policy set per scope (effective-date resolution); operator workflow to publish versions with rationale.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit


def _policy_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "artifacts" / "policy"


def list_policy_artifacts(workspace_root: Path) -> List[Dict[str, Any]]:
    """List known policy artifact files (trust_and_budget, regulatory, event_taxonomy, etc.) with paths."""
    root = _policy_root(workspace_root)
    if not root.exists():
        return []
    out = []
    for f in sorted(root.glob("*.yaml")):
        if f.name.endswith(".example.yaml"):
            continue
        out.append({"name": f.stem, "path": str(f), "type": "yaml"})
    return out


def get_active_policy_set(
    workspace_root: Path,
    scope_type: str = "global",
    scope_id: str = "default",
    at_ts: Optional[str] = None,
) -> Dict[str, Any]:
    """Return active policy set for scope: trust_and_budget (from stakes) and regulatory (from affective)."""
    from hg_core.stakes.policy import load_policy as load_trust_policy
    from hg_core.affective.policy import load_regulatory_policy
    workspace_root = Path(workspace_root)
    trust = load_trust_policy(workspace_root)
    regulatory = load_regulatory_policy(workspace_root)
    return {
        "scope_type": scope_type,
        "scope_id": scope_id,
        "trust_and_budget": trust,
        "regulatory": regulatory,
    }


def publish_policy(
    *,
    policy_type: str,
    artifact_path: str,
    version: Optional[str] = None,
    scope: Dict[str, str],
    actor: Dict[str, str],
    rationale_artifact_id: Optional[str] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit POLICY_PUBLISHED. policy_type e.g. trust_and_budget, regulatory, rbac. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    import hashlib
    obj_id = "pol_" + hashlib.sha256(f"{policy_type}:{artifact_path}:{version or ''}".encode()).hexdigest()[:16]
    payload = {"policy_type": policy_type, "artifact_path": artifact_path}
    if version:
        payload["version"] = version
    if rationale_artifact_id:
        payload["rationale_artifact_id"] = rationale_artifact_id
    return emit(
        "POLICY_PUBLISHED",
        "policy",
        obj_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def record_policy_applied(
    *,
    scope: Dict[str, str],
    policy_ref: str,
    context: Optional[Dict[str, Any]] = None,
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit POLICY_APPLIED (which policy set was used in a decision/run). Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    import hashlib
    import time
    obj_id = "app_" + hashlib.sha256(f"{policy_ref}{time.time()}".encode()).hexdigest()[:16]
    payload = {"policy_ref": policy_ref}
    if context:
        payload["context"] = context
    return emit(
        "POLICY_APPLIED",
        "policy",
        obj_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def apply_policy_override(
    *,
    scope: Dict[str, str],
    override_spec: Dict[str, Any],
    expiry_ts: str,
    actor: Dict[str, str],
    rationale: str,
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit POLICY_OVERRIDE_APPLIED (scoped override with expiry). Returns event_id."""
    if not expiry_ts:
        raise ValueError("expiry_ts required for policy override")
    workspace_root = Path(workspace_root or ".")
    import hashlib
    import time
    obj_id = "ovr_" + hashlib.sha256(f"{scope}{override_spec}{expiry_ts}{time.time()}".encode()).hexdigest()[:16]
    payload = {"override_spec": override_spec, "expiry_ts": expiry_ts}
    if rationale:
        payload["rationale"] = rationale
    return emit(
        "POLICY_OVERRIDE_APPLIED",
        "policy",
        obj_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
