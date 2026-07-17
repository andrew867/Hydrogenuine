"""Forbidden claim checking for domain packs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ClaimCheckResult:
    allowed: bool
    blocked_claims: list[str]
    reason: str


def check_forbidden_claims(text: str, pack: Mapping[str, Any]) -> ClaimCheckResult:
    lowered = text.lower()
    blocked: list[str] = []
    for item in pack.get("forbidden_claims", []):
        claim = item.get("claim") if isinstance(item, Mapping) else str(item)
        if claim and str(claim).lower() in lowered:
            blocked.append(str(claim))
    if blocked:
        return ClaimCheckResult(False, blocked, "FORBIDDEN_CLAIM_BLOCKED")
    return ClaimCheckResult(True, [], "OK")


__all__ = ["ClaimCheckResult", "check_forbidden_claims"]
