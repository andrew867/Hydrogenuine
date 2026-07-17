"""EXCITON situational awareness panels — freshness, digest, alerts, timeline."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from hg_runtime.exciton.alerts import build_alert_strip
from hg_runtime.exciton.away_digest import build_away_digest
from hg_runtime.exciton.chrono_expiry import clock_confidence_payload
from hg_runtime.exciton.data_freshness import assess_freshness
from hg_runtime.exciton.decision_timeline import build_decision_timeline
from hg_runtime.exciton.schema import ExcitonPanelState
from hg_runtime.exciton.ui_state import UIViewState, describe_ui_state
from hg_runtime.bounded_soak.stop_panic_runtime import operator_semantics, stop_panic_state


from hg_runtime.exciton.schema import ExcitonPanelState, ExcitonPanelStatus


def _panel(
    panel_id: str,
    title: str,
    *,
    state: ExcitonPanelState,
    fields: dict[str, Any],
    human_summary: str,
) -> ExcitonPanelStatus:
    payload = dict(fields)
    payload.setdefault("human_summary", human_summary)
    payload.setdefault("data_tier", "LIVE")
    payload.setdefault("advisory_only", True)
    payload.setdefault("permission_granted", False)
    payload.setdefault("authority_created", False)
    return ExcitonPanelStatus(
        panel_id=panel_id,
        title=title,
        source="situational_awareness",
        state=state,
        fields=payload,
    )


def _state_from_freshness(fresh: dict[str, Any]) -> ExcitonPanelState:
    s = fresh.get("state", "GREEN")
    if s == "CONTACT_LOST":
        return ExcitonPanelState.RED
    if s == "STALE":
        return ExcitonPanelState.YELLOW
    return ExcitonPanelState.GREEN


def _parse(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None


def build_situational_panels(
    *, generated_at: str | None = None, offline_fixture: bool = False
) -> list[ExcitonPanelStatus]:
    now = generated_at or datetime.now(timezone.utc).isoformat()
    # In the offline fixture snapshot the data is intentionally static — evaluate freshness/alerts
    # against the fixture's own reference time so the panel is deterministically fresh (GREEN) and
    # the snapshot hash is stable. LIVE mode (offline_fixture=False) keeps real-clock staleness ⇒
    # RED with approvals disabled.
    ref = _parse(now) if offline_fixture else None
    fresh = assess_freshness(generated_at=now, now=ref)
    digest = build_away_digest()
    alerts = build_alert_strip(snapshot_generated_at=now, now=ref)
    timeline = build_decision_timeline()
    chrono = clock_confidence_payload()
    sp = stop_panic_state()
    sem = operator_semantics()
    ui_home = describe_ui_state(UIViewState.GREEN if fresh["state"] == "GREEN" else UIViewState.STALE)

    freshness_state = _state_from_freshness(fresh)
    alert_state = ExcitonPanelState.RED if any(a.get("severity") == "RED" for a in alerts.get("alerts", [])) else ExcitonPanelState.GREEN
    if alerts.get("alerts") and alert_state != ExcitonPanelState.RED:
        alert_state = ExcitonPanelState.YELLOW

    panels = [
        _panel(
            "DataFreshnessPanel",
            "Data Freshness",
            state=freshness_state,
            fields={
                **fresh,
                "data_updated_at": now,
                "generated_at": now,
            },
            human_summary=fresh.get("human_message", ""),
        ),
        _panel(
            "AwayDigestPanel",
            "While You Were Away",
            state=ExcitonPanelState.YELLOW if digest.get("incidents") else ExcitonPanelState.GREEN,
            fields=digest,
            human_summary=digest.get("human_summary", ""),
        ),
        _panel(
            "OperatorAlertsPanel",
            "Operator Alerts",
            state=alert_state,
            fields=alerts,
            human_summary=alerts.get("human_summary", "No alerts."),
        ),
        _panel(
            "DecisionTimelinePanel",
            "Decision Timeline",
            state=ExcitonPanelState.GREEN,
            fields={
                "event_count": len(timeline),
                "events": timeline[:25],
            },
            human_summary=f"{len(timeline)} receipt-backed events.",
        ),
        _panel(
            "ChronoConfidencePanel",
            "CHRONO Time Confidence",
            state=ExcitonPanelState.YELLOW if chrono.get("time_uncertain") else ExcitonPanelState.GREEN,
            fields=chrono,
            human_summary=chrono.get("human_message", ""),
        ),
        _panel(
            "StopPanicSemanticsPanel",
            "Stop / Panic Semantics",
            state=ExcitonPanelState.RED if sp.panic_active else (ExcitonPanelState.YELLOW if sp.stop_active else ExcitonPanelState.GREEN),
            fields={
                "stop_active": sp.stop_active,
                "panic_active": sp.panic_active,
                "stop_semantics": sem.get("STOP"),
                "panic_semantics": sem.get("PANIC"),
            },
            human_summary="STOP = graceful halt; PANIC = immediate block until reset.",
        ),
        _panel(
            "UIStateModelPanel",
            "UI State Model",
            state=ExcitonPanelState.GREEN,
            fields={
                "cockpit_home": ui_home,
                "states": [s.value for s in UIViewState],
            },
            human_summary="Empty/loading/stale/error/degraded/green/red — never fake GREEN.",
        ),
    ]
    return panels


__all__ = ["build_situational_panels"]
