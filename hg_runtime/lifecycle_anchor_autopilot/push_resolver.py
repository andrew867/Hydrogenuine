"""Resolve lifecycle GitHub anchor push from config, credentials, and operator env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_runtime.external_start_anchor.credentials import (
    CredentialMode,
    apply_canonical_env,
    resolve_credential_status,
)

WORKSPACE = Path(__file__).resolve().parents[2]


def _env_tri(name: str) -> bool | None:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return None
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return None


@dataclass
class LifecyclePushPolicy:
    push_requested: bool
    lifecycle_autopush_enabled: bool
    dry_run: bool
    config_allow_push: bool
    credentials_ok: bool
    credential_mode: str
    reason: str
    verdict: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "push_requested": self.push_requested,
            "lifecycle_autopush_enabled": self.lifecycle_autopush_enabled,
            "dry_run": self.dry_run,
            "config_allow_push": self.config_allow_push,
            "credentials_ok": self.credentials_ok,
            "credential_mode": self.credential_mode,
            "reason": self.reason,
            "verdict": self.verdict,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


def _credentials_ready(creds: Any) -> bool:
    return creds.mode not in {CredentialMode.ABSENT, CredentialMode.INVALID_CONFIG}


def resolve_lifecycle_push_policy(
    *,
    workspace: Path | None = None,
    config_path: str | Path | None = None,
) -> LifecyclePushPolicy:
    """Config + SSH/token credentials enable push; env may only restrict or explicitly enable."""
    from hg_runtime.external_witness_journal.agent0_context import load_journal_config

    apply_canonical_env()
    cfg = load_journal_config(config_path)
    creds = resolve_credential_status()
    creds_ok = _credentials_ready(creds)

    allow_env = _env_tri("HG_ANCHOR_ALLOW_PUSH")
    autopush_env = _env_tri("HG_LIFECYCLE_AUTOPUSH_ENABLED")

    if allow_env is False:
        return LifecyclePushPolicy(
            push_requested=False,
            lifecycle_autopush_enabled=False,
            dry_run=True,
            config_allow_push=cfg.allow_push,
            credentials_ok=creds_ok,
            credential_mode=creds.mode.value,
            reason="HG_ANCHOR_ALLOW_PUSH=false blocks remote push",
            verdict="YELLOW_LOCAL_ONLY_ANCHOR_NOT_REMOTE",
        )

    if autopush_env is False:
        return LifecyclePushPolicy(
            push_requested=False,
            lifecycle_autopush_enabled=False,
            dry_run=True,
            config_allow_push=cfg.allow_push,
            credentials_ok=creds_ok,
            credential_mode=creds.mode.value,
            reason="HG_LIFECYCLE_AUTOPUSH_ENABLED=false blocks lifecycle autopush",
            verdict="YELLOW_LOCAL_ONLY_ANCHOR_NOT_REMOTE",
        )

    if not cfg.allow_push:
        return LifecyclePushPolicy(
            push_requested=False,
            lifecycle_autopush_enabled=False,
            dry_run=True,
            config_allow_push=False,
            credentials_ok=creds_ok,
            credential_mode=creds.mode.value,
            reason="github_anchor config allow_push=false",
            verdict="YELLOW_LOCAL_ONLY_ANCHOR_NOT_REMOTE",
        )

    if not creds_ok:
        return LifecyclePushPolicy(
            push_requested=False,
            lifecycle_autopush_enabled=False,
            dry_run=True,
            config_allow_push=True,
            credentials_ok=False,
            credential_mode=creds.mode.value,
            reason="anchor credentials absent — local commit only",
            verdict="YELLOW_LOCAL_ONLY_ANCHOR_NOT_REMOTE",
        )

    # Config allow_push + credentials: autopush unless env explicitly disables.
    autopush_on = autopush_env if autopush_env is not None else True
    allow_on = allow_env if allow_env is not None else True
    live = autopush_on and allow_on

    if live:
        return LifecyclePushPolicy(
            push_requested=True,
            lifecycle_autopush_enabled=True,
            dry_run=False,
            config_allow_push=True,
            credentials_ok=True,
            credential_mode=creds.mode.value,
            reason="config allow_push + credentials + lifecycle autopush policy",
            verdict="GREEN_LIFECYCLE_ANCHOR_AUTOPUSH_READY",
        )

    return LifecyclePushPolicy(
        push_requested=False,
        lifecycle_autopush_enabled=False,
        dry_run=True,
        config_allow_push=True,
        credentials_ok=True,
        credential_mode=creds.mode.value,
        reason="operator env restricted push despite config/credentials",
        verdict="YELLOW_LOCAL_ONLY_ANCHOR_NOT_REMOTE",
    )


__all__ = ["LifecyclePushPolicy", "resolve_lifecycle_push_policy"]
