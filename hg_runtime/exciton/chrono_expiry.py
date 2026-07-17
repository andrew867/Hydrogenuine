"""CHRONO confidence coupling for auto-approval expiry."""

from __future__ import annotations

from typing import Any

CONFIDENCE_THRESHOLD = 0.7


def chrono_expiry_context(*, time_confidence: float | None = None, chrono_ref: str | None = None) -> dict[str, Any]:
    conf = time_confidence if time_confidence is not None else 1.0
    uncertain = conf < CONFIDENCE_THRESHOLD
    return {
        "chrono_ref": chrono_ref,
        "time_confidence": conf,
        "time_uncertain": uncertain,
        "auto_approval_allowed": not uncertain,
        "human_message": (
            "Clock confidence low — expiry-based auto-approval requires manual review."
            if uncertain
            else "Clock confidence sufficient for expiry checks."
        ),
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }


def deny_auto_approval_if_clock_uncertain(time_confidence: float | None) -> tuple[bool, str]:
    ctx = chrono_expiry_context(time_confidence=time_confidence)
    if ctx["time_uncertain"]:
        return False, "RED_AUTO_APPROVAL_WITH_UNTRUSTED_CLOCK"
    return True, "ok"


def clock_confidence_payload(*, time_confidence: float | None = None, chrono_ref: str | None = None) -> dict[str, Any]:
    return chrono_expiry_context(time_confidence=time_confidence, chrono_ref=chrono_ref)


__all__ = [
    "CONFIDENCE_THRESHOLD",
    "chrono_expiry_context",
    "clock_confidence_payload",
    "deny_auto_approval_if_clock_uncertain",
]
