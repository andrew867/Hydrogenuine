"""Lifecycle anchor autopilot hooks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hg_runtime.lifecycle_anchor_autopilot.dispatcher import dispatch_lifecycle_event
from hg_runtime.lifecycle_anchor_autopilot.schema import LifecycleAnchorEvent

WORKSPACE = Path(__file__).resolve().parents[2]


def _handoff(path: str | Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def dispatch_boot_start(**kwargs: Any) -> dict[str, Any]:
    return dispatch_lifecycle_event(LifecycleAnchorEvent.BOOT_START, kwargs.pop("summary", "Boot starting."), **kwargs)


def dispatch_wake_refresh_start(**kwargs: Any) -> dict[str, Any]:
    return dispatch_lifecycle_event(LifecycleAnchorEvent.WRR_START, kwargs.pop("summary", "Wake refresh starting."), **kwargs)


def dispatch_wake_refresh_complete(verdict: str, **kwargs: Any) -> dict[str, Any]:
    facts = kwargs.pop("facts", {})
    facts = {**facts, "wake_readiness": verdict}
    return dispatch_lifecycle_event(
        LifecycleAnchorEvent.WRR_COMPLETE,
        kwargs.pop("summary", f"Wake refresh complete: {verdict}."),
        facts=facts,
        **kwargs,
    )


def dispatch_first_wake_start(**kwargs: Any) -> dict[str, Any]:
    return dispatch_lifecycle_event(LifecycleAnchorEvent.FIRST_WAKE_START, kwargs.pop("summary", "First wake starting."), **kwargs)


def dispatch_first_wake_complete(verdict: str, **kwargs: Any) -> dict[str, Any]:
    facts = kwargs.pop("facts", {})
    facts = {**facts, "mission_verdict": verdict}
    return dispatch_lifecycle_event(
        LifecycleAnchorEvent.FIRST_WAKE_COMPLETE,
        kwargs.pop("summary", f"First wake complete: {verdict}."),
        facts=facts,
        **kwargs,
    )


def dispatch_weather_voice_start(**kwargs: Any) -> dict[str, Any]:
    return dispatch_lifecycle_event(LifecycleAnchorEvent.WEATHER_VOICE_START, kwargs.pop("summary", "Weather voice starting."), **kwargs)


def dispatch_weather_voice_complete(verdict: str, **kwargs: Any) -> dict[str, Any]:
    facts = kwargs.pop("facts", {})
    facts = {**facts, "mission_verdict": verdict}
    return dispatch_lifecycle_event(
        LifecycleAnchorEvent.WEATHER_VOICE_COMPLETE,
        kwargs.pop("summary", f"Weather voice complete: {verdict}."),
        facts=facts,
        **kwargs,
    )


def dispatch_sleep_start(**kwargs: Any) -> dict[str, Any]:
    return dispatch_lifecycle_event(LifecycleAnchorEvent.SLEEP_START, kwargs.pop("summary", "Sleep starting."), **kwargs)


def dispatch_sleep_complete(**kwargs: Any) -> dict[str, Any]:
    return dispatch_lifecycle_event(LifecycleAnchorEvent.SLEEP_COMPLETE, kwargs.pop("summary", "Sleep complete."), **kwargs)


def dispatch_clean_stop(**kwargs: Any) -> dict[str, Any]:
    return dispatch_lifecycle_event(LifecycleAnchorEvent.CLEAN_STOP, kwargs.pop("summary", "Clean stop."), **kwargs)


def dispatch_panic_entered(**kwargs: Any) -> dict[str, Any]:
    return dispatch_lifecycle_event(LifecycleAnchorEvent.PANIC_ENTERED, kwargs.pop("summary", "Panic entered."), **kwargs)


def dispatch_panic_cleared(**kwargs: Any) -> dict[str, Any]:
    return dispatch_lifecycle_event(LifecycleAnchorEvent.PANIC_CLEARED, kwargs.pop("summary", "Panic cleared."), **kwargs)
