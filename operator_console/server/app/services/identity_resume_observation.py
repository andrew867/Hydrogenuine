from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _parse_timestamp(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _isoformat_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def build_identity_resume_observation(
    *,
    identity_continuity_summary: dict[str, Any] | None,
    continuity_recovery_ack: dict[str, Any] | None,
) -> dict[str, Any]:
    identity_continuity_summary = identity_continuity_summary if isinstance(identity_continuity_summary, dict) else {}
    continuity_recovery_ack = continuity_recovery_ack if isinstance(continuity_recovery_ack, dict) else {}

    acknowledged_at = _parse_timestamp(continuity_recovery_ack.get("acknowledged_at"))
    last_wake_at = _parse_timestamp(identity_continuity_summary.get("last_wake_at"))
    wake_receipt_recorded_at = _parse_timestamp(identity_continuity_summary.get("wake_receipt_recorded_at"))
    identity_status = str(identity_continuity_summary.get("status") or "").strip().lower()
    observed_at = max(
        [timestamp for timestamp in (last_wake_at, wake_receipt_recorded_at) if timestamp is not None],
        default=None,
    )

    if acknowledged_at is None:
        return {
            "status": "not_required",
            "observation_required": False,
            "observation_complete": False,
            "acknowledged_at": None,
            "observed_at": None,
            "summary": "identity_resume_observation_not_required",
        }

    observation_complete = identity_status == "healthy" and observed_at is not None and observed_at >= acknowledged_at
    return {
        "status": "observed" if observation_complete else "pending",
        "observation_required": True,
        "observation_complete": observation_complete,
        "acknowledged_at": _isoformat_utc(acknowledged_at),
        "observed_at": _isoformat_utc(observed_at) if observation_complete else None,
        "summary": "identity_resume_observed" if observation_complete else "identity_resume_observation_pending",
    }
