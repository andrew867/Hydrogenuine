"""EXCITON data freshness and staleness alarms."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

WARNING_STALE_SECONDS = 30
HARD_STALE_SECONDS = 120


def _parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None


def assess_freshness(
    *,
    generated_at: str | None,
    expected_poll_seconds: float = 15.0,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    gen = _parse_ts(generated_at)
    if not gen:
        return {
            "state": "STALE",
            "age_seconds": None,
            "warning_threshold_seconds": WARNING_STALE_SECONDS,
            "hard_stale_threshold_seconds": HARD_STALE_SECONDS,
            "approvals_disabled": True,
            "human_message": "No snapshot timestamp — contact lost.",
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }
    age = (now - gen).total_seconds()
    state = "GREEN"
    approvals_disabled = False
    if age >= HARD_STALE_SECONDS:
        state = "CONTACT_LOST"
        approvals_disabled = True
    elif age >= WARNING_STALE_SECONDS:
        state = "STALE"
        approvals_disabled = True
    return {
        "state": state,
        "age_seconds": round(age, 1),
        "last_updated_ago": f"{int(age)}s ago",
        "warning_threshold_seconds": WARNING_STALE_SECONDS,
        "hard_stale_threshold_seconds": HARD_STALE_SECONDS,
        "expected_poll_seconds": expected_poll_seconds,
        "approvals_disabled": approvals_disabled,
        "human_message": _msg(state, age),
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }


def _msg(state: str, age: float) -> str:
    if state == "CONTACT_LOST":
        return f"Backend contact lost ({int(age)}s stale). Approvals disabled."
    if state == "STALE":
        return f"Data is stale ({int(age)}s old). Refresh before approving."
    return "Data is fresh."


__all__ = ["HARD_STALE_SECONDS", "WARNING_STALE_SECONDS", "assess_freshness"]
