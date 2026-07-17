"""Credential scope verification — read-only required."""

from __future__ import annotations

import os
from typing import Any

from hg_runtime.live_read_endurance.errors import LiveReadWriteScopeDetected
from hg_runtime.live_read_endurance.schema import (
    LiveReadCredentialScope,
    LiveReadEnduranceVerdict,
    load_policy,
    new_id,
    now_iso,
)
from hg_runtime.social_capability.credentials import enforce_live_read_only_env, load_operator_social_env
from hg_runtime.social_capability.live_bridge import LiveReadSurface, credential_status_for_surface, live_read_enabled
from hg_runtime.social_capability.read_receipts import LiveReadCredentialStatus


def _write_scope_detected() -> bool:
    if os.environ.get("HG_ENABLE_LIVE_SOCIAL_WRITES", "").lower() in ("1", "true", "yes"):
        return True
    if os.environ.get("HG_SOCIAL_LIVE_PUBLISH", "").lower() in ("1", "true", "yes"):
        return True
    if os.environ.get("HG_SOCIAL_LIVE_REPLY", "").lower() in ("1", "true", "yes"):
        return True
    if os.environ.get("HG_EXTERNAL_SEND_ENABLED", "").lower() in ("1", "true", "yes"):
        return True
    return False


def check_credential_scope(surface: LiveReadSurface = LiveReadSurface.MOLTBOOK) -> LiveReadCredentialScope:
    load_operator_social_env()
    policy = load_policy()
    write_allowed = _write_scope_detected()
    read_allowed = live_read_enabled()
    cred = credential_status_for_surface(surface)

    if policy.get("write_scope_allowed") is False and write_allowed:
        raise LiveReadWriteScopeDetected("RED_LIVE_READ_WRITE_SCOPE_DETECTED")

    enforce_live_read_only_env()

    if cred == LiveReadCredentialStatus.CREDENTIALS_MISSING:
        verdict = LiveReadEnduranceVerdict.YELLOW_LIVE_READ_CREDENTIALS_MISSING
    elif not read_allowed:
        verdict = LiveReadEnduranceVerdict.YELLOW_LIVE_READ_CREDENTIALS_MISSING
    elif write_allowed:
        verdict = LiveReadEnduranceVerdict.RED_LIVE_READ_WRITE_SCOPE_DETECTED
    else:
        verdict = LiveReadEnduranceVerdict.GREEN_LIVE_READ_ENDURANCE_COMPLETE

    scope = LiveReadCredentialScope(
        credential_scope_id=new_id("cred-scope"),
        source_kind=surface.value,
        source_name=surface.value,
        read_allowed=read_allowed and cred == LiveReadCredentialStatus.CREDENTIALS_PRESENT,
        write_allowed=write_allowed,
        scopes_observed=("read",) if read_allowed else tuple(),
        configured_ref=f"env:{surface.value}",
        checked_at=now_iso(),
        verdict=verdict,
    ).with_hash()
    return scope


def credential_summary() -> dict[str, Any]:
    from hg_runtime.social_capability.credentials import operator_social_env_sources

    load_operator_social_env()
    enforce_live_read_only_env()
    scopes = []
    for surface in (LiveReadSurface.MOLTBOOK, LiveReadSurface.FOURCLAW):
        try:
            scopes.append(check_credential_scope(surface).to_payload())
        except LiveReadWriteScopeDetected:
            scopes.append({"source_kind": surface.value, "verdict": "RED_LIVE_READ_WRITE_SCOPE_DETECTED"})
    return {
        "live_read_enabled": live_read_enabled(),
        "write_scope_detected": _write_scope_detected(),
        "operator_env_sources": operator_social_env_sources(),
        "scopes": scopes,
        "credential_values_printed": False,
    }
