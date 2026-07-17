"""
Gateway repository for secret_aliases and social_accounts (Social Media Entity Tools).
CRUD using hg_gateway.db.get_connection; used by Keystore API and adapters to resolve account credentials.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from hg_gateway.db import get_connection, _get_db_path


def _get_conn(db_path: Optional[str] = None):
    return get_connection(db_path or _get_db_path())


# ---- secret_aliases ----


def secret_alias_get(alias_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetch a secret alias by alias_id. Returns dict with provider_kind, provider_ref, purpose, metadata_json, etc."""
    with _get_conn(db_path) as conn:
        row = conn.execute(
            "SELECT alias_id, provider_kind, provider_ref, purpose, metadata_json, created_at, disabled_at FROM secret_aliases WHERE alias_id = ?",
            (alias_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "alias_id": row[0],
            "provider_kind": row[1],
            "provider_ref": row[2],
            "purpose": row[3],
            "metadata_json": row[4],
            "created_at": row[5],
            "disabled_at": row[6],
        }


def secret_alias_list(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all secret aliases (non-disabled)."""
    with _get_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT alias_id, provider_kind, provider_ref, purpose, metadata_json, created_at, disabled_at FROM secret_aliases WHERE disabled_at IS NULL ORDER BY created_at"
        ).fetchall()
        return [
            {
                "alias_id": r[0],
                "provider_kind": r[1],
                "provider_ref": r[2],
                "purpose": r[3],
                "metadata_json": r[4],
                "created_at": r[5],
                "disabled_at": r[6],
            }
            for r in rows
        ]


def secret_alias_create(
    alias_id: str,
    provider_kind: str,
    provider_ref: str,
    purpose: str,
    metadata_json: Optional[Dict[str, Any]] = None,
    db_path: Optional[str] = None,
) -> None:
    """Insert a secret alias."""
    with _get_conn(db_path) as conn:
        conn.execute(
            "INSERT INTO secret_aliases (alias_id, provider_kind, provider_ref, purpose, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, datetime('now'))",
            (alias_id, provider_kind, provider_ref, purpose, json.dumps(metadata_json or {})),
        )


def secret_alias_disable(alias_id: str, db_path: Optional[str] = None) -> None:
    """Soft-disable a secret alias by setting disabled_at."""
    with _get_conn(db_path) as conn:
        conn.execute("UPDATE secret_aliases SET disabled_at = datetime('now') WHERE alias_id = ?", (alias_id,))


# ---- social_accounts ----


def social_account_get(social_account_id: str, tenant_id: str = "default", db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetch a social account by id and tenant."""
    with _get_conn(db_path) as conn:
        row = conn.execute(
            "SELECT social_account_id, tenant_id, platform, account_alias, login_secret_alias_id, mfa_secret_alias_id, entity_scope, persona_scope, state, created_at FROM social_accounts WHERE social_account_id = ? AND tenant_id = ?",
            (social_account_id, tenant_id),
        ).fetchone()
        if not row:
            return None
        return {
            "social_account_id": row[0],
            "tenant_id": row[1],
            "platform": row[2],
            "account_alias": row[3],
            "login_secret_alias_id": row[4],
            "mfa_secret_alias_id": row[5],
            "entity_scope": row[6],
            "persona_scope": row[7],
            "state": row[8],
            "created_at": row[9],
        }


def social_account_get_by_alias(account_alias: str, tenant_id: str = "default", db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetch a social account by account_alias and tenant."""
    with _get_conn(db_path) as conn:
        row = conn.execute(
            "SELECT social_account_id, tenant_id, platform, account_alias, login_secret_alias_id, mfa_secret_alias_id, entity_scope, persona_scope, state, created_at FROM social_accounts WHERE account_alias = ? AND tenant_id = ?",
            (account_alias, tenant_id),
        ).fetchone()
        if not row:
            return None
        return {
            "social_account_id": row[0],
            "tenant_id": row[1],
            "platform": row[2],
            "account_alias": row[3],
            "login_secret_alias_id": row[4],
            "mfa_secret_alias_id": row[5],
            "entity_scope": row[6],
            "persona_scope": row[7],
            "state": row[8],
            "created_at": row[9],
        }


def social_account_list(tenant_id: str = "default", platform: Optional[str] = None, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """List social accounts for tenant, optionally filtered by platform."""
    with _get_conn(db_path) as conn:
        if platform:
            rows = conn.execute(
                "SELECT social_account_id, tenant_id, platform, account_alias, login_secret_alias_id, mfa_secret_alias_id, entity_scope, persona_scope, state, created_at FROM social_accounts WHERE tenant_id = ? AND platform = ? ORDER BY created_at",
                (tenant_id, platform),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT social_account_id, tenant_id, platform, account_alias, login_secret_alias_id, mfa_secret_alias_id, entity_scope, persona_scope, state, created_at FROM social_accounts WHERE tenant_id = ? ORDER BY created_at",
                (tenant_id,),
            ).fetchall()
        return [
            {
                "social_account_id": r[0],
                "tenant_id": r[1],
                "platform": r[2],
                "account_alias": r[3],
                "login_secret_alias_id": r[4],
                "mfa_secret_alias_id": r[5],
                "entity_scope": r[6],
                "persona_scope": r[7],
                "state": r[8],
                "created_at": r[9],
            }
            for r in rows
        ]


def social_account_create(
    social_account_id: str,
    platform: str,
    account_alias: str,
    tenant_id: str = "default",
    login_secret_alias_id: Optional[str] = None,
    mfa_secret_alias_id: Optional[str] = None,
    entity_scope: Optional[str] = None,
    persona_scope: Optional[str] = None,
    state: str = "unverified",
    db_path: Optional[str] = None,
) -> None:
    """Insert a social account."""
    with _get_conn(db_path) as conn:
        conn.execute(
            "INSERT INTO social_accounts (social_account_id, tenant_id, platform, account_alias, login_secret_alias_id, mfa_secret_alias_id, entity_scope, persona_scope, state, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
            (social_account_id, tenant_id, platform, account_alias, login_secret_alias_id, mfa_secret_alias_id, entity_scope, persona_scope, state),
        )


def social_account_update_state(social_account_id: str, tenant_id: str, state: str, db_path: Optional[str] = None) -> None:
    """Update social account state (e.g. unverified -> verified)."""
    with _get_conn(db_path) as conn:
        conn.execute(
            "UPDATE social_accounts SET state = ? WHERE social_account_id = ? AND tenant_id = ?",
            (state, social_account_id, tenant_id),
        )


def social_account_attach_secret_alias(
    social_account_id: str,
    tenant_id: str,
    *,
    login_secret_alias_id: Optional[str] = None,
    mfa_secret_alias_id: Optional[str] = None,
    db_path: Optional[str] = None,
) -> None:
    """Attach or update secret aliases for a social account."""
    updates: list[str] = []
    values: list[Optional[str]] = []
    if login_secret_alias_id is not None:
        updates.append("login_secret_alias_id = ?")
        values.append(login_secret_alias_id)
    if mfa_secret_alias_id is not None:
        updates.append("mfa_secret_alias_id = ?")
        values.append(mfa_secret_alias_id)
    if not updates:
        return
    values.extend([social_account_id, tenant_id])
    with _get_conn(db_path) as conn:
        conn.execute(
            f"UPDATE social_accounts SET {', '.join(updates)} WHERE social_account_id = ? AND tenant_id = ?",
            tuple(values),
        )


def resolve_provider_ref_for_alias(alias_id: str, db_path: Optional[str] = None) -> Optional[str]:
    """Resolve alias_id to provider_ref for use with KeystoreService.resolve(provider_ref). Returns None if disabled or missing."""
    with _get_conn(db_path) as conn:
        row = conn.execute(
            "SELECT provider_ref, disabled_at FROM secret_aliases WHERE alias_id = ?",
            (alias_id,),
        ).fetchone()
        if not row or row[1] is not None:
            return None
        return row[0]
