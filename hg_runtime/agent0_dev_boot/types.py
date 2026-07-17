"""Agent #0 dev boot shared types."""

from __future__ import annotations

from typing import Any, Literal

AGENT0_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-15T00:15:00.000000Z"

BootVerdict = Literal[
    "GREEN_AGENT0_PREP_READY",
    "GREEN_AGENT0_BOOT",
    "YELLOW_AGENT0_PREP_READY_STORAGE_PENDING",
    "YELLOW_STORAGE_PENDING",
    "YELLOW_FALLBACK_STUB_ONLY",
    "RED_AGENT0_PREP_FAILED",
    "RED_AUTHORITY_CONVERSION",
]


def advisory_payload(**fields: Any) -> dict[str, Any]:
    base = {
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
        "is_permit": False,
        "consciousness_claim": False,
        "authority_claim": False,
    }
    base.update(fields)
    if base.get("permission_granted") or base.get("authority_created"):
        raise ValueError("agent0 dev boot must not grant permission or authority")
    return base


__all__ = ["AGENT0_SCHEMA_VERSION", "FIXTURE_CLOCK", "BootVerdict", "advisory_payload"]
