"""
Keystore API for entity tools (Social Media Entity Tools).
GET /api/v1/keystore/accounts — list social accounts by tenant/platform.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from operator_console.server.app.services.social_account_summary import build_social_account_operator_summary

from hg_core.human_notifications import list_human_notifications
from hg_core.browser.playwright_runtime import get_playwright_runtime
from hg_core.browser.session_health import (
    browser_session_is_reusable,
    evaluate_browser_session_health,
    mark_browser_session_degraded,
)
from hg_core.security import (
    KeystoreService,
    SecretAliasDisabledError,
    SecretAliasNotFoundError,
    SecretResolutionError,
    SocialAccountBindingError,
    SocialAccountNotFoundError,
    SocialAccountStateError,
    get_latest_bound_browser_session_id,
    get_default_provider,
    record_social_account_session_binding,
    record_social_account_artifact,
)
from hg_gateway import keystore_repo
from hg_gateway.db import _get_db_path, get_connection
from hg_lib.config import get_workspace_root

router = APIRouter(tags=["keystore-entity"])


def _tenant_id(x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")) -> str:
    return (x_tenant_id or "").strip() or "default"


def _keystore() -> KeystoreService:
    return KeystoreService(get_default_provider())


def _map_keystore_error(exc: Exception) -> HTTPException:
    if isinstance(exc, SocialAccountNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, (SocialAccountStateError, SecretAliasDisabledError, SocialAccountBindingError)):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, (SecretAliasNotFoundError, SecretResolutionError)):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


def _load_json_file(path: Optional[str]) -> Optional[Dict[str, Any]]:
    if not path:
        return None
    try:
        p = Path(path)
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _latest_session_for_account(account: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    binding_session = _latest_bound_session_for_account(account["social_account_id"])
    if binding_session:
        return binding_session
    entity_scope = (account.get("entity_scope") or "").strip()
    if not entity_scope:
        return None
    with get_connection(_get_db_path()) as conn:
        row = conn.execute(
            """SELECT browser_session_id, tenant_id, entity_id, platform, state, started_at, ended_at, trace_path, latest_screenshot_path
               FROM browser_sessions
               WHERE tenant_id = ? AND entity_id = ? AND platform = ?
               ORDER BY started_at DESC, browser_session_id DESC
               LIMIT 1""",
            (account["tenant_id"], entity_scope, account["platform"]),
        ).fetchone()
        if not row:
            return None
        return {
            "browser_session_id": row[0],
            "tenant_id": row[1],
            "entity_id": row[2],
            "platform": row[3],
            "state": row[4],
            "started_at": row[5],
            "ended_at": row[6],
            "trace_path": row[7],
            "latest_screenshot_path": row[8],
        }


def _session_by_id(session_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
    with get_connection(_get_db_path()) as conn:
        row = conn.execute(
            """SELECT browser_session_id, tenant_id, entity_id, platform, state, started_at, ended_at, trace_path, latest_screenshot_path
               FROM browser_sessions
               WHERE browser_session_id = ? AND tenant_id = ?""",
            (session_id, tenant_id),
        ).fetchone()
        if not row:
            return None
        return {
            "browser_session_id": row[0],
            "tenant_id": row[1],
            "entity_id": row[2],
            "platform": row[3],
            "state": row[4],
            "started_at": row[5],
            "ended_at": row[6],
            "trace_path": row[7],
            "latest_screenshot_path": row[8],
        }


def _artifacts_for_related(related_kind: str, related_id: str) -> list[Dict[str, Any]]:
    with get_connection(_get_db_path()) as conn:
        rows = conn.execute(
            """SELECT proof_id, artifact_type, path, metadata_json, created_at
               FROM proof_artifacts
               WHERE related_kind = ? AND related_id = ?
               ORDER BY created_at DESC, proof_id DESC""",
            (related_kind, related_id),
        ).fetchall()
        return [
            {
                "proof_id": row[0],
                "artifact_type": row[1],
                "path": row[2],
                "metadata": json.loads(row[3]) if row[3] else {},
                "created_at": row[4],
            }
            for row in rows
        ]


def _artifacts_for_session(session_id: str) -> list[Dict[str, Any]]:
    return _artifacts_for_related("browser_session", session_id)


def _artifacts_for_account(social_account_id: str) -> list[Dict[str, Any]]:
    return _artifacts_for_related("social_account", social_account_id)


def _latest_bound_session_for_account(social_account_id: str) -> Optional[Dict[str, Any]]:
    artifacts = _artifacts_for_account(social_account_id)
    session_id = get_latest_bound_browser_session_id(social_account_id)
    binding = next((item for item in artifacts if item["artifact_type"] == "browser_session_binding"), None)
    payload = _load_json_file(binding["path"]) if binding else {}
    tenant_id = ((payload or {}).get("tenant_id") or "default").strip() or "default"
    if not session_id:
        return None
    return _session_by_id(session_id, tenant_id)


def _latest_account_artifact_payload(
    account_artifacts: list[Dict[str, Any]],
    artifact_types: set[str],
) -> Optional[Dict[str, Any]]:
    artifact = next((item for item in account_artifacts if item.get("artifact_type") in artifact_types), None)
    if not artifact:
        return None
    payload = _load_json_file(artifact.get("path"))
    if payload is None:
        return None
    if "artifact_type" not in payload:
        payload["artifact_type"] = artifact.get("artifact_type")
    if "created_at" not in payload:
        payload["created_at"] = artifact.get("created_at")
    return payload


def _recent_human_notifications(account: Dict[str, Any], limit: int = 10) -> list[Dict[str, Any]]:
    platform = str(account.get("platform") or "").strip().lower()
    social_account_id = str(account.get("social_account_id") or "").strip()
    if not platform:
        return []
    matches: list[Dict[str, Any]] = []
    for row in list_human_notifications(get_workspace_root(), limit=max(50, limit * 5)):
        if not isinstance(row, dict):
            continue
        notification_social_account_id = str(row.get("social_account_id") or "").strip()
        if social_account_id and notification_social_account_id:
            if notification_social_account_id != social_account_id:
                continue
            matches.append(row)
            if len(matches) >= max(1, limit):
                break
            continue
        summary = row.get("summary") if isinstance(row.get("summary"), dict) else {}
        execution = summary.get("execution") if isinstance(summary, dict) else {}
        execution = execution if isinstance(execution, dict) else {}
        notification_platform = str(execution.get("platform") or "").strip().lower()
        task_name = str(row.get("task_name") or "").strip().lower()
        if notification_platform != platform and platform not in task_name:
            continue
        matches.append(row)
        if len(matches) >= max(1, limit):
            break
    return matches


def _browser_session_health(
    session: Optional[Dict[str, Any]],
    artifacts: list[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    return evaluate_browser_session_health(session, artifacts)


def _social_account_readiness(
    account: Dict[str, Any],
    *,
    latest_session: Optional[Dict[str, Any]],
    latest_browser_session_health: Optional[Dict[str, Any]],
    latest_registration_proof: Optional[Dict[str, Any]],
    latest_verification_proof: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    account_state = str(account.get("state") or "").strip().lower()
    continuity_status = str((latest_browser_session_health or {}).get("status") or "").strip().lower()
    checks = {
        "account_usable_state": account_state in {"active", "verified", "pending"},
        "login_binding_present": bool(account.get("login_secret_alias_id")),
        "browser_session_present": latest_session is not None,
        "continuity_healthy": continuity_status != "degraded",
        "proof_present": bool(latest_verification_proof or latest_registration_proof),
    }
    blocking = [name for name, ok in checks.items() if not ok and name != "browser_session_present"]
    return {
        "ready": not blocking,
        "checks": checks,
        "blocking": blocking,
        "summary": {
            "state": account_state or None,
            "browser_session_id": latest_session.get("browser_session_id") if latest_session else None,
            "continuity_status": latest_browser_session_health.get("status") if latest_browser_session_health else None,
        },
    }


def _session_is_reusable(
    session: Optional[Dict[str, Any]],
    *,
    artifacts: list[Dict[str, Any]],
) -> bool:
    return browser_session_is_reusable(session, artifacts=artifacts)


class CreateAccountBody(BaseModel):
    platform: str
    account_alias: str
    entity_scope: Optional[str] = None
    persona_scope: Optional[str] = None
    state: str = "unverified"
    social_account_id: Optional[str] = None


class AttachSecretBody(BaseModel):
    secret_kind: str
    alias_id: str


class StartLoginSessionBody(BaseModel):
    entity_id: Optional[str] = None


class VerifyLoginBody(BaseModel):
    entity_id: Optional[str] = None


class RecordAccountProofBody(BaseModel):
    artifact_type: str = "registration_proof"
    label: Optional[str] = None
    handle: Optional[str] = None
    url: Optional[str] = None
    note: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    state: Optional[str] = None


@router.get("/accounts")
def list_accounts(
    platform: Optional[str] = None,
    entity_scope: Optional[str] = None,
    persona_scope: Optional[str] = None,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """List social accounts for tenant, optionally by platform."""
    tenant = _tenant_id(x_tenant_id)
    items = keystore_repo.social_account_list(tenant_id=tenant, platform=platform)
    if entity_scope:
        expected = entity_scope.strip()
        items = [item for item in items if str(item.get("entity_scope") or "").strip() == expected]
    if persona_scope:
        expected = persona_scope.strip()
        items = [item for item in items if str(item.get("persona_scope") or "").strip() == expected]
    return {"items": items}


@router.post("/accounts")
def create_account(
    body: CreateAccountBody,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """Create a social account binding in the keystore catalog."""
    tenant = _tenant_id(x_tenant_id)
    social_account_id = body.social_account_id or str(uuid.uuid4())
    try:
        keystore_repo.social_account_create(
            social_account_id=social_account_id,
            tenant_id=tenant,
            platform=body.platform,
            account_alias=body.account_alias,
            entity_scope=body.entity_scope,
            persona_scope=body.persona_scope,
            state=body.state,
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail=f"Unable to create social account: {exc}") from exc
    account = keystore_repo.social_account_get(social_account_id, tenant_id=tenant)
    return {"item": account}


@router.post("/accounts/{social_account_id}/attach-secret")
def attach_secret(
    social_account_id: str,
    body: AttachSecretBody,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """Attach a login or MFA secret alias to an existing social account."""
    tenant = _tenant_id(x_tenant_id)
    account = keystore_repo.social_account_get(social_account_id, tenant_id=tenant)
    if not account:
        raise HTTPException(status_code=404, detail="Social account not found")
    alias = keystore_repo.secret_alias_get(body.alias_id)
    if not alias:
        raise HTTPException(status_code=404, detail=f"Secret alias not found: {body.alias_id}")
    if alias.get("disabled_at"):
        raise HTTPException(status_code=409, detail=f"Secret alias disabled: {body.alias_id}")
    kind = body.secret_kind.strip().lower()
    if kind == "login":
        keystore_repo.social_account_attach_secret_alias(
            social_account_id,
            tenant,
            login_secret_alias_id=body.alias_id,
        )
    elif kind == "mfa":
        keystore_repo.social_account_attach_secret_alias(
            social_account_id,
            tenant,
            mfa_secret_alias_id=body.alias_id,
        )
    else:
        raise HTTPException(status_code=400, detail="secret_kind must be one of: login, mfa")
    updated = keystore_repo.social_account_get(social_account_id, tenant_id=tenant)
    return {"item": updated}


@router.get("/accounts/resolve-task/{task_name}")
def resolve_task_account(
    task_name: str,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """Resolve the single assigned social account for an automation task."""
    tenant = _tenant_id(x_tenant_id)
    try:
        item = _keystore().resolve_task_social_account(task_name, tenant_id=tenant)
    except Exception as exc:
        raise _map_keystore_error(exc) from exc
    return {"item": item}


@router.post("/accounts/{social_account_id}/start-login-session")
def start_login_session(
    social_account_id: str,
    body: Optional[StartLoginSessionBody] = None,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """Start a supervised browser session for a social account."""
    tenant = _tenant_id(x_tenant_id)
    try:
        account = _keystore().get_social_account(
            social_account_id=social_account_id,
            tenant_id=tenant,
            entity_id=(body.entity_id if body else None),
            allow_states={"active", "verified", "pending", "unverified"},
        )
    except Exception as exc:
        raise _map_keystore_error(exc) from exc
    entity_id = (body.entity_id if body else None) or account.get("entity_scope") or "operator"
    runtime = get_playwright_runtime()
    bound_session_id = get_latest_bound_browser_session_id(account["social_account_id"])
    bound_state = runtime.get_session_state(bound_session_id, tenant_id=tenant) if bound_session_id else None
    bound_artifacts = _artifacts_for_session(bound_session_id) if bound_session_id else []
    bound_health = _browser_session_health(bound_state, bound_artifacts) if bound_session_id else None
    replaced_degraded_session = None
    if bound_session_id and bound_health and bound_health.get("status") == "degraded":
        mark_browser_session_degraded(
            bound_session_id,
            tenant,
            reason="missing_restart_critical_browser_artifacts",
        )
        replaced_degraded_session = {
            "browser_session_id": bound_session_id,
            "reason": "missing_restart_critical_browser_artifacts",
            "previous_health": bound_health,
        }
    session_id = (
        bound_session_id
        if _session_is_reusable(bound_state, artifacts=bound_artifacts)
        else runtime.start_session(entity_id, account["platform"], tenant_id=tenant)
    )
    binding = record_social_account_session_binding(
        social_account_id=account["social_account_id"],
        browser_session_id=session_id,
        platform=account["platform"],
        tenant_id=tenant,
        entity_id=entity_id,
        account_alias=account.get("account_alias"),
        state="active",
    )
    return {
        "browser_session_id": session_id,
        "social_account_id": account["social_account_id"],
        "account_alias": account["account_alias"],
        "entity_id": entity_id,
        "platform": account["platform"],
        "state": "active",
        "replaced_degraded_session": replaced_degraded_session,
        "session_binding_artifact": binding,
    }


@router.post("/accounts/{social_account_id}/verify-login")
def verify_login(
    social_account_id: str,
    body: Optional[VerifyLoginBody] = None,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """Verify that a social account can resolve its assigned login bundle."""
    tenant = _tenant_id(x_tenant_id)
    try:
        resolved = _keystore().resolve_social_account(
            social_account_id=social_account_id,
            tenant_id=tenant,
            entity_id=(body.entity_id if body else None),
        )
    except Exception as exc:
        raise _map_keystore_error(exc) from exc
    keystore_repo.social_account_update_state(social_account_id, tenant, "verified")
    proof_payload = {
        "social_account_id": resolved.social_account_id,
        "account_alias": resolved.account_alias,
        "platform": resolved.platform,
        "tenant_id": tenant,
        "entity_scope": resolved.entity_scope,
        "persona_scope": resolved.persona_scope,
        "verified": True,
        "state": "verified",
        "login_secret_present": bool(resolved.login_secret),
        "mfa_secret_present": bool(resolved.mfa_secret),
    }
    artifact = record_social_account_artifact(
        resolved.social_account_id,
        artifact_type="verification_proof",
        label="verify-login",
        payload=proof_payload,
        metadata={
            "source": "keystore.verify_login",
            "account_alias": resolved.account_alias,
            "platform": resolved.platform,
            "verified": True,
        },
    )
    return {
        "verified": True,
        "social_account_id": resolved.social_account_id,
        "account_alias": resolved.account_alias,
        "platform": resolved.platform,
        "state": "verified",
        "login_secret_present": bool(resolved.login_secret),
        "mfa_secret_present": bool(resolved.mfa_secret),
        "artifact": artifact,
    }


@router.post("/accounts/{social_account_id}/proof-artifacts")
def record_account_proof_artifact(
    social_account_id: str,
    body: RecordAccountProofBody,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """Persist registration/proof metadata directly against a social account."""
    tenant = _tenant_id(x_tenant_id)
    account = keystore_repo.social_account_get(social_account_id, tenant_id=tenant)
    if not account:
        raise HTTPException(status_code=404, detail="Social account not found")

    artifact_type = (body.artifact_type or "").strip() or "registration_proof"
    label = (body.label or "").strip() or artifact_type.replace("/", "-")
    payload = dict(body.payload or {})
    if body.handle:
        payload["handle"] = body.handle
    if body.url:
        payload["url"] = body.url
    if body.note:
        payload["note"] = body.note
    payload.setdefault("social_account_id", social_account_id)
    payload.setdefault("account_alias", account.get("account_alias"))
    payload.setdefault("platform", account.get("platform"))
    payload.setdefault("tenant_id", tenant)

    artifact = record_social_account_artifact(
        social_account_id,
        artifact_type=artifact_type,
        label=label,
        payload=payload,
        metadata={
            "label": label,
            "handle": body.handle,
            "url": body.url,
            "note_present": bool(body.note),
        },
    )
    if body.state:
        keystore_repo.social_account_update_state(social_account_id, tenant, body.state)
    updated = keystore_repo.social_account_get(social_account_id, tenant_id=tenant)
    return {"item": updated, "artifact": artifact, "payload": payload}


@router.post("/accounts/{social_account_id}/lock")
def lock_account(
    social_account_id: str,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """Lock a social account to prevent further automated use."""
    tenant = _tenant_id(x_tenant_id)
    account = keystore_repo.social_account_get(social_account_id, tenant_id=tenant)
    if not account:
        raise HTTPException(status_code=404, detail="Social account not found")
    keystore_repo.social_account_update_state(social_account_id, tenant, "locked")
    updated = keystore_repo.social_account_get(social_account_id, tenant_id=tenant)
    return {"item": updated}


@router.get("/accounts/{social_account_id}/overview")
def account_overview(
    social_account_id: str,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """Return account state plus latest browser session and notification digest."""
    tenant = _tenant_id(x_tenant_id)
    account = keystore_repo.social_account_get(social_account_id, tenant_id=tenant)
    if not account:
        raise HTTPException(status_code=404, detail="Social account not found")
    latest_session = _latest_session_for_account(account)
    artifacts = _artifacts_for_session(latest_session["browser_session_id"]) if latest_session else []
    account_artifacts = _artifacts_for_account(social_account_id)
    latest_digest_artifact = next((item for item in artifacts if item["artifact_type"] == "notification_digest"), None)
    latest_digest = _load_json_file(latest_digest_artifact["path"]) if latest_digest_artifact else None
    latest_registration_artifact = next(
        (item for item in account_artifacts if item["artifact_type"] in {"registration_proof", "account_proof", "verification_proof"}),
        None,
    )
    latest_registration_proof = _load_json_file(latest_registration_artifact["path"]) if latest_registration_artifact else None
    latest_post_proof = _latest_account_artifact_payload(account_artifacts, {"post_proof"})
    latest_reply_proof = _latest_account_artifact_payload(account_artifacts, {"reply_proof"})
    latest_challenge_proof = _latest_account_artifact_payload(account_artifacts, {"challenge_proof"})
    latest_verification_proof = _latest_account_artifact_payload(account_artifacts, {"verification_proof", "account_proof"})
    recent_human_notifications = _recent_human_notifications(account)
    latest_browser_session_health = _browser_session_health(latest_session, artifacts)
    shared_summary = build_social_account_operator_summary(social_account_id, account=account)
    readiness = shared_summary.get("readiness_summary") or _social_account_readiness(
        account,
        latest_session=latest_session,
        latest_browser_session_health=latest_browser_session_health,
        latest_registration_proof=latest_registration_proof,
        latest_verification_proof=latest_verification_proof,
    )
    return {
        "item": account,
        "latest_browser_session": latest_session,
        "latest_browser_session_health": latest_browser_session_health,
        "readiness": readiness,
        "proof_summary": shared_summary.get("proof_summary"),
        "continuity_summary": shared_summary.get("continuity_summary"),
        "continuity_injury_summary": shared_summary.get("continuity_injury_summary"),
        "notification_summary": shared_summary.get("notification_summary"),
        "last_activity_summary": shared_summary.get("last_activity_summary"),
        "latest_notification_digest": latest_digest,
        "latest_artifacts": artifacts[:10],
        "account_artifacts": account_artifacts[:10],
        "latest_registration_proof": latest_registration_proof,
        "latest_post_proof": latest_post_proof,
        "latest_reply_proof": latest_reply_proof,
        "latest_challenge_proof": latest_challenge_proof,
        "latest_verification_proof": latest_verification_proof,
        "recent_human_notifications": recent_human_notifications,
    }
