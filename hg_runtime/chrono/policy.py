"""CHRONO authority boundary — time is evidence, not authority."""

from __future__ import annotations

from typing import Any


class ChronoBoundaryViolation(Exception):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def reject_authority_mutation(payload: dict[str, Any]) -> dict[str, Any]:
    """A time reading can never grant permission or create authority."""
    if payload.get("permission_granted") is True or payload.get("authority_created") is True:
        return {
            "schema": "chrono-authority-conversion-rejected",
            "rejected": True,
            "reason": "CHRONO time is evidence, not authority",
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }
    return {"schema": "chrono-authority-check-ok", "rejected": False}


def attempt_time_authorization(capability_id: str) -> dict[str, Any]:
    """Explicit rejection path when time is misused to authorize an action."""
    return reject_authority_mutation({"permission_granted": True, "capability_id": capability_id})


def validate_frozen_constants(payload: dict[str, Any]) -> list[str]:
    """Return a list of frozen-constant violations (empty == ok)."""
    failures: list[str] = []
    if payload.get("advisory_only") is not True:
        failures.append("advisory_only must be True")
    if payload.get("permission_granted") is not False:
        failures.append("permission_granted must be False")
    if payload.get("authority_created") is not False:
        failures.append("authority_created must be False")
    return failures


__all__ = [
    "ChronoBoundaryViolation",
    "attempt_time_authorization",
    "reject_authority_mutation",
    "validate_frozen_constants",
]
