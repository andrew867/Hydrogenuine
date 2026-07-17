"""Trust Boundary policy — taint monotonicity, authority rejection, frozen guards."""

from __future__ import annotations

from typing import Any

from hg_runtime.trust_boundary.schema import TaintLabel, trust_rank


class TrustBoundaryViolation(Exception):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def assert_taint_monotonic(old: TaintLabel, new: TaintLabel) -> None:
    """A relabel may never increase trust rank (untrusted -> trusted forbidden)."""
    if trust_rank(new) > trust_rank(old):
        raise TrustBoundaryViolation(
            "TAINT_MONOTONICITY",
            f"forbidden relabel {old.value} -> {new.value} (trust upgrade)",
        )


def relabel(old: TaintLabel, new: TaintLabel) -> TaintLabel:
    assert_taint_monotonic(old, new)
    return new


def reject_authority_mutation(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("permission_granted") is True or payload.get("authority_created") is True:
        return {
            "schema": "tb-authority-conversion-rejected",
            "rejected": True,
            "reason": "external content cannot grant permission or authority",
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }
    return {"schema": "tb-authority-check-ok", "rejected": False}


def validate_frozen_constants(payload: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if payload.get("advisory_only") is not True:
        failures.append("advisory_only must be True")
    if payload.get("permission_granted") is not False:
        failures.append("permission_granted must be False")
    if payload.get("authority_created") is not False:
        failures.append("authority_created must be False")
    return failures


__all__ = [
    "TrustBoundaryViolation",
    "assert_taint_monotonic",
    "reject_authority_mutation",
    "relabel",
    "validate_frozen_constants",
]
