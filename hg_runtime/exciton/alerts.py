"""Operator attention alerts — local visual strip, no approval pressure."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from hg_runtime.exciton.away_digest import build_away_digest
from hg_runtime.exciton.data_freshness import assess_freshness


class AlertSeverity(str, Enum):
    INFO = "INFO"
    REVIEW_NEEDED = "REVIEW_NEEDED"
    YELLOW = "YELLOW"
    RED = "RED"
    PANIC = "PANIC"


def build_alert_strip(*, snapshot_generated_at: str | None = None, now: datetime | None = None) -> dict[str, Any]:
    # ``now`` lets the offline-fixture snapshot evaluate freshness against the fixture reference
    # time (deterministic, fresh) instead of the wall clock. Live callers pass nothing → real now.
    freshness = assess_freshness(generated_at=snapshot_generated_at, now=now)
    digest = build_away_digest()
    alerts: list[dict[str, Any]] = []

    if freshness["state"] in ("STALE", "CONTACT_LOST"):
        alerts.append(_alert(AlertSeverity.RED, "Data stale", freshness["human_message"]))
    if digest.get("stop_panic", {}).get("panic"):
        alerts.append(_alert(AlertSeverity.PANIC, "Panic stop", "Immediate halt active."))
    elif digest.get("stop_panic", {}).get("stop"):
        alerts.append(_alert(AlertSeverity.YELLOW, "Stop active", "No new side effects."))
    if digest.get("pending_approvals", 0) > 0:
        alerts.append(_alert(
            AlertSeverity.REVIEW_NEEDED,
            "Review needed",
            f"{digest['pending_approvals']} item(s) await your review.",
        ))
    for inc in digest.get("incidents", []):
        if inc.startswith("RED"):
            alerts.append(_alert(AlertSeverity.RED, "Incident", inc))

    return {
        "alerts": alerts,
        "highest_severity": alerts[0]["severity"] if alerts else AlertSeverity.INFO.value,
        "can_approve": not freshness.get("approvals_disabled"),
        "pressure_to_approve": False,
        "human_summary": alerts[0]["message"] if alerts else "No alerts.",
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }


def _alert(severity: AlertSeverity, title: str, message: str) -> dict[str, str]:
    return {"severity": severity.value, "title": title, "message": message}


__all__ = ["AlertSeverity", "build_alert_strip"]
