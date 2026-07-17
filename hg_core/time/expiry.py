"""Validity windows — stale authority refused at boundary (CT-11 TIM-U4)."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any

import yaml

from hg_core.time.clock import parse_rfc3339_z

STALE_APPROVAL = "admission.refused.stale_approval"
DRY_RUN_EXPIRED = "tim.refused.dry_run_expired"
DRY_RUN_HASH_CHANGED = "tim.refused.dry_run_hash_changed"
STALE_CONFIRMATION = STALE_APPROVAL

_CONFIG_CACHE: dict[str, Any] | None = None


def default_config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "time_windows_v1.yaml"


def load_time_windows(path: Path | None = None) -> dict[str, Any]:
    global _CONFIG_CACHE
    cfg_path = path or default_config_path()
    if _CONFIG_CACHE is not None and path is None:
        return _CONFIG_CACHE
    payload = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    if path is None:
        _CONFIG_CACHE = payload
    return payload


def reset_time_windows_cache() -> None:
    global _CONFIG_CACHE
    _CONFIG_CACHE = None


def is_expired(expires_at: str, now: str) -> bool:
    """Fail closed on unknown; refuse at expires_at (valid at expires_at - 1ms)."""
    expiry = parse_rfc3339_z(expires_at)
    current = parse_rfc3339_z(now)
    if expiry is None or current is None:
        return True
    return current >= expiry


def validate_approval_window(expires_at: str | None, now: str) -> tuple[bool, str]:
    if not expires_at:
        return True, "ok"
    if is_expired(expires_at, now):
        return False, STALE_APPROVAL
    return True, "ok"


def validate_confirmation_window(expires_at: str | None, now: str) -> tuple[bool, str]:
    if not expires_at:
        return True, "ok"
    if is_expired(expires_at, now):
        return False, STALE_CONFIRMATION
    return True, "ok"


def validate_dry_run_window(
    *,
    dry_run_created_at: str,
    dry_run_input_hash: str,
    current_input_hash: str,
    now: str,
    ttl_seconds: float | None = None,
) -> tuple[bool, str]:
    if dry_run_input_hash != current_input_hash:
        return False, DRY_RUN_HASH_CHANGED
    created = parse_rfc3339_z(dry_run_created_at)
    current = parse_rfc3339_z(now)
    if created is None or current is None:
        return False, DRY_RUN_EXPIRED
    ttl = ttl_seconds
    if ttl is None:
        ttl = float(load_time_windows().get("dry_run_ttl_seconds", 300))
    if current >= created + timedelta(seconds=ttl):
        return False, DRY_RUN_EXPIRED
    return True, "ok"


__all__ = [
    "DRY_RUN_EXPIRED",
    "DRY_RUN_HASH_CHANGED",
    "STALE_APPROVAL",
    "STALE_CONFIRMATION",
    "is_expired",
    "load_time_windows",
    "reset_time_windows_cache",
    "validate_approval_window",
    "validate_confirmation_window",
    "validate_dry_run_window",
]
