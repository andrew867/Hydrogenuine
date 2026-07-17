"""Provider routing profile loader."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hg_runtime.cloud_browser_governance.types import advisory_envelope

PROFILES_DIR = Path(__file__).resolve().parents[2] / "configs" / "runtime"


def load_routing_profile(path: Path | str) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        p = PROFILES_DIR / p.name
    data = json.loads(p.read_text(encoding="utf-8"))
    for key in ("cloud_providers_enabled", "external_network_allowed", "permission_granted", "authority_created", "live_oea", "live_ter", "srp_apply", "publish"):
        if key in data and data[key] is True and key in {"permission_granted", "authority_created", "live_oea", "live_ter", "srp_apply", "publish"}:
            raise ValueError(f"unsafe routing profile: {key}=true")
    return data


def list_routing_profiles() -> list[Path]:
    return sorted(PROFILES_DIR.glob("provider-routing-*.json"))


def profile_summary(profile: dict[str, Any]) -> dict[str, Any]:
    return advisory_envelope(
        schema="provider-routing-summary",
        profile_id=profile.get("profile_id"),
        agent0_main=profile.get("agent0_main_provider_role"),
        agent0_fallback=profile.get("agent0_fallback_provider_role"),
        cloud_enabled=profile.get("cloud_providers_enabled", False),
        external_network=profile.get("external_network_allowed", False),
        hourly_token_budget=profile.get("hourly_token_budget"),
        daily_cost_budget_usd=profile.get("daily_cost_budget_usd"),
    )


__all__ = ["PROFILES_DIR", "list_routing_profiles", "load_routing_profile", "profile_summary"]
