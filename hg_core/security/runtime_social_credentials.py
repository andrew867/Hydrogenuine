"""Runtime credential resolution for task-scoped social accounts."""

from __future__ import annotations

import json
import os
from typing import Callable, Iterable, Optional

from hg_core.security import KeystoreService, get_default_provider


def resolve_runtime_task_name(task_name: Optional[str] = None) -> Optional[str]:
    """Resolve the current runtime task name from explicit arg or environment."""
    candidate = (task_name or "").strip()
    if candidate:
        return candidate
    for env_key in ("HG_RUNTIME_TASK_NAME", "HG_TASK_NAME", "HG_CURRENT_TASK_NAME"):
        candidate = (os.environ.get(env_key) or "").strip()
        if candidate:
            return candidate
    return None


def runtime_tenant_id() -> str:
    """Resolve runtime tenant id consistently with operator surfaces."""
    return (os.getenv("HG_OPERATOR_TENANT_ID") or os.getenv("HG_DEFAULT_TENANT_ID") or "default").strip() or "default"


def is_keystore_first_task(task_name: Optional[str]) -> bool:
    """Whether the task must resolve social credentials through keystore first."""
    candidate = (task_name or "").strip().lower()
    return candidate.startswith("newfoundland-bayman-")


def _extract_secret_value(secret: str, credential_keys: Iterable[str]) -> Optional[str]:
    raw = str(secret or "").strip()
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return raw
    if isinstance(payload, dict):
        for key in credential_keys:
            value = payload.get(key)
            if value:
                return str(value).strip()
    return raw


def resolve_task_platform_credential(
    *,
    platform: str,
    credential_keys: Iterable[str],
    task_name: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> Optional[str]:
    """
    Resolve a credential for the runtime task from its assigned keystore-backed social account.

    For keystore-first tasks, account/binding errors are allowed to propagate so callers fail closed.
    For legacy tasks, errors degrade to None so existing env/file fallback continues to work.
    """
    resolved_task_name = resolve_runtime_task_name(task_name)
    if not resolved_task_name:
        return None
    service = KeystoreService(get_default_provider())
    try:
        account = service.resolve_social_account(
            social_account_id=service.resolve_task_social_account(
                resolved_task_name,
                tenant_id=tenant_id or runtime_tenant_id(),
            ).get("social_account_id"),
            tenant_id=tenant_id or runtime_tenant_id(),
            platform=platform,
        )
    except Exception:
        if is_keystore_first_task(resolved_task_name):
            raise
        return None
    return _extract_secret_value(account.login_secret, credential_keys)


def resolve_task_social_account_id(
    *,
    platform: Optional[str] = None,
    task_name: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> Optional[str]:
    """
    Resolve the social_account_id assigned to the runtime task.

    For keystore-first tasks, binding errors propagate so callers fail closed.
    For legacy tasks, errors degrade to None.
    """
    resolved_task_name = resolve_runtime_task_name(task_name)
    if not resolved_task_name:
        return None
    service = KeystoreService(get_default_provider())
    try:
        account = service.resolve_task_social_account(
            resolved_task_name,
            tenant_id=tenant_id or runtime_tenant_id(),
        )
    except Exception:
        if is_keystore_first_task(resolved_task_name):
            raise
        return None
    social_account_id = account.get("social_account_id")
    if not social_account_id:
        return None
    if platform:
        account_platform = str(account.get("platform") or "").strip().lower()
        if account_platform and account_platform != platform.strip().lower():
            if is_keystore_first_task(resolved_task_name):
                raise ValueError(
                    f"Resolved social account platform mismatch for task {resolved_task_name}: "
                    f"expected {platform}, got {account.get('platform')}"
                )
            return None
    return str(social_account_id)


def attach_runtime_proof_state(
    result: dict,
    *,
    platform: str,
    persist_artifact: Callable[[str], Optional[dict]],
    task_name: Optional[str] = None,
    tenant_id: Optional[str] = None,
    explicit_social_account_id: Optional[str] = None,
) -> dict:
    """
    Attach a stable proof_state payload to runtime results.

    This keeps social runtimes honest about whether a durable account-bound proof
    was attached, skipped because no binding exists, or failed because resolution
    or persistence broke.
    """
    resolved_task_name = resolve_runtime_task_name(task_name)
    resolved_tenant_id = (tenant_id or runtime_tenant_id()).strip() or "default"
    proof_state = {
        "platform": platform,
        "tenant_id": resolved_tenant_id,
        "task_name": resolved_task_name,
        "keystore_first_task": is_keystore_first_task(resolved_task_name),
        "status": "pending",
    }

    social_account_id = explicit_social_account_id
    if social_account_id:
        proof_state["social_account_id"] = social_account_id
        proof_state["binding_source"] = "explicit"
    else:
        try:
            social_account_id = resolve_task_social_account_id(
                platform=platform,
                task_name=resolved_task_name,
                tenant_id=resolved_tenant_id,
            )
        except Exception as exc:
            proof_state["status"] = "binding_error"
            proof_state["reason"] = str(exc)
            result["proof_state"] = proof_state
            result["proof_artifact_error"] = str(exc)
            return result
        if social_account_id:
            proof_state["social_account_id"] = social_account_id
            proof_state["binding_source"] = "task"

    if not social_account_id:
        proof_state["status"] = "missing_binding"
        proof_state["reason"] = "no_resolved_social_account"
        result["proof_state"] = proof_state
        return result

    try:
        artifact = persist_artifact(social_account_id)
    except Exception as exc:
        proof_state["status"] = "artifact_error"
        proof_state["reason"] = str(exc)
        result["proof_state"] = proof_state
        result["proof_artifact_error"] = str(exc)
        return result

    if artifact:
        result["proof_artifact"] = artifact
        proof_state["status"] = "attached"
        proof_state["artifact_type"] = artifact.get("artifact_type")
        proof_state["artifact_path"] = artifact.get("path")
    else:
        proof_state["status"] = "skipped"
        proof_state["reason"] = "persist_artifact_returned_none"

    result["proof_state"] = proof_state
    return result
