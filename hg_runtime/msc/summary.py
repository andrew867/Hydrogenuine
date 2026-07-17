"""Deterministic Phase 0 meditation summary — no LLM, no tools."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from hg_core.ledger.canonical_json import canonical_dumps
from hg_runtime.contract import jsonable
from hg_runtime.msc.types import MeditationSummary
from hg_runtime.msc.window import _subsystem_from_type


def _count_by_subsystem(events: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        subsystem = _subsystem_from_type(str(event.get("type", "")))
        counts[subsystem] = counts.get(subsystem, 0) + 1
    return dict(sorted(counts.items()))


def _latest_status(view: Mapping[str, Any]) -> dict[str, Any]:
    activity = view.get("activity", {})
    env = view.get("environment", {})
    if not isinstance(activity, Mapping):
        activity = {}
    if not isinstance(env, Mapping):
        env = {}
    return {
        "aep": {
            "max_severity": env.get("arousal", {}).get("max_severity", 0)
            if isinstance(env.get("arousal"), Mapping)
            else 0,
            "signals_recorded": activity.get("aep", {}).get("signals_recorded", 0)
            if isinstance(activity.get("aep"), Mapping)
            else 0,
        },
        "crr": {
            "recovery_state": env.get("recovery_state", "NORMAL"),
            "cycles": activity.get("crr", {}).get("cycles", 0)
            if isinstance(activity.get("crr"), Mapping)
            else 0,
        },
        "oea": activity.get("oea", {}) if isinstance(activity.get("oea"), Mapping) else {},
        "ter": activity.get("ter", {}) if isinstance(activity.get("ter"), Mapping) else {},
        "srp": activity.get("srp", {}) if isinstance(activity.get("srp"), Mapping) else {},
        "csm": activity.get("csm", {}) if isinstance(activity.get("csm"), Mapping) else {},
        "mel": activity.get("mel", {}) if isinstance(activity.get("mel"), Mapping) else {},
    }


def _refusals_and_failures(events: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    keys = (
        "REFUSED",
        "FAILED",
        "DENIED",
        "BLOCKED",
    )
    counts: dict[str, int] = {}
    for event in events:
        etype = str(event.get("type", ""))
        if any(fragment in etype for fragment in keys):
            counts[etype] = counts.get(etype, 0) + 1
    return dict(sorted(counts.items()))


def build_deterministic_summary(
    *,
    summary_id: str,
    agent_id: str,
    cycle_id: str,
    events: Sequence[Mapping[str, Any]],
    event_hashes: Sequence[str],
    view: Mapping[str, Any],
    world_state_hash: str,
    redaction_report_ref: str | None = None,
) -> MeditationSummary:
    """Build a stable, observation-only summary."""
    safe_view = jsonable(view)
    env = safe_view.get("environment", {}) if isinstance(safe_view, dict) else {}
    health = env.get("health", {}) if isinstance(env, dict) else {}
    structured = {
        "event_counts_by_subsystem": _count_by_subsystem(events),
        "subsystem_status": _latest_status(safe_view),
        "recent_refusals_failures": _refusals_and_failures(events),
        "world_state_hash": world_state_hash,
        "unresolved_alerts": {
            "panic": bool(env.get("panic")) if isinstance(env, dict) else False,
            "recovery_state": env.get("recovery_state", "NORMAL") if isinstance(env, dict) else "NORMAL",
            "handler_failures": health.get("handler_failures", 0) if isinstance(health, dict) else 0,
        },
        "observation_only": True,
        "authority": None,
    }
    digest = hashlib.sha256(canonical_dumps(structured)).hexdigest()
    return MeditationSummary(
        summary_id=summary_id,
        agent_id=agent_id,
        cycle_id=cycle_id,
        input_event_hashes=tuple(event_hashes),
        input_world_state_hash=world_state_hash,
        generated_by="deterministic",
        summary=structured,
        summary_hash=f"sha256:{digest}",
        redaction_report_ref=redaction_report_ref,
    )


__all__ = ["build_deterministic_summary"]
