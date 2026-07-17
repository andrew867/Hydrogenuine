"""Runtime profile loader and validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hg_runtime.agent0_dev_boot.types import advisory_payload

PROFILES_DIR = Path(__file__).resolve().parents[2] / "configs" / "runtime"

REQUIRED_BOOL_SAFETY = (
    "external_network_allowed",
    "cloud_providers_enabled",
    "live_oea",
    "live_ter",
    "srp_apply",
    "publish",
    "child_spawn",
    "permission_granted",
    "authority_created",
)


def load_runtime_profile(path: Path | str) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file() and not str(path).startswith("/"):
        p = PROFILES_DIR / p.name
    data = json.loads(p.read_text(encoding="utf-8"))
    validate_runtime_profile(data)
    return data


def validate_runtime_profile(data: dict[str, Any]) -> None:
    for key in ("profile_id", "purpose", "duration_budget_minutes", "token_budget", "heartbeat_interval_seconds"):
        if key not in data:
            raise ValueError(f"runtime profile missing {key}")
    for key in REQUIRED_BOOL_SAFETY:
        if key not in data:
            raise ValueError(f"runtime profile missing safety field {key}")
        if data[key] is True and key in {
            "live_oea", "live_ter", "srp_apply", "publish", "child_spawn",
            "permission_granted", "authority_created",
        }:
            raise ValueError(f"unsafe runtime profile flip: {key}=true")
    if data.get("cloud_providers_enabled") and not data.get("external_network_allowed"):
        raise ValueError("cloud providers require explicit external_network_allowed")
    advisory_payload(**{k: data.get(k, False) for k in ("permission_granted", "authority_created")})


def list_runtime_profiles() -> list[Path]:
    paths: list[Path] = []
    for p in sorted(PROFILES_DIR.glob("*.json")):
        name = p.name
        if name.startswith("provider-routing-") or name.startswith("browser-"):
            continue
        paths.append(p)
    return paths


__all__ = ["PROFILES_DIR", "load_runtime_profile", "list_runtime_profiles", "validate_runtime_profile"]
