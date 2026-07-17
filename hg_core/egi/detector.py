"""EGI fixture repeated-pattern detector — no permissions created."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence

from hg_core.egi.schemas import EmergentBehaviorObservation, SensitivityClass

DEFAULT_REPEAT_THRESHOLD = 3
FIXTURE_CLOCK = "2026-06-12T18:00:00.000000Z"


def _event_field(event: Mapping[str, Any], key: str, default: str = "") -> str:
    return str(event.get(key, default) or default)


def detect_repeated_patterns(
    events: Sequence[Mapping[str, Any]],
    *,
    threshold: int = DEFAULT_REPEAT_THRESHOLD,
    observed_at: str | None = None,
) -> list[EmergentBehaviorObservation]:
    """Group fixture events by behavior_label; emit observations when threshold met."""
    if threshold < 2:
        raise ValueError("threshold must be >= 2")
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for event in events:
        label = _event_field(event, "behavior_label")
        if not label:
            continue
        groups[label].append(event)

    now = observed_at or FIXTURE_CLOCK
    observations: list[EmergentBehaviorObservation] = []
    for label, grouped in sorted(groups.items()):
        if len(grouped) < threshold:
            continue
        timestamps = sorted(_event_field(e, "timestamp", now) for e in grouped)
        source_refs = tuple(sorted({_event_field(e, "source_ref", _event_field(e, "event_id")) for e in grouped}))
        sensitivity = _classify_sensitivity(grouped)
        observations.append(
            EmergentBehaviorObservation(
                observation_id=f"egi_obs_{label}",
                observed_at=now,
                source_refs=source_refs,
                behavior_label=label,
                behavior_description=_event_field(grouped[-1], "description", f"Repeated {label}"),
                repeated_count=len(grouped),
                first_seen=timestamps[0],
                last_seen=timestamps[-1],
                context_refs=tuple(sorted({_event_field(e, "context_ref") for e in grouped if e.get("context_ref")})),
                triggering_events=tuple(_event_field(e, "event_id", f"evt_{i}") for i, e in enumerate(grouped)),
                failure_refs=tuple(
                    _event_field(e, "event_id")
                    for e in grouped
                    if e.get("outcome") == "failure"
                ),
                success_refs=tuple(
                    _event_field(e, "event_id")
                    for e in grouped
                    if e.get("outcome") == "success"
                ),
                operator_feedback_refs=tuple(
                    _event_field(e, "feedback_ref")
                    for e in grouped
                    if e.get("feedback_ref")
                ),
                affected_modules=tuple(sorted({_event_field(e, "module") for e in grouped if e.get("module")})),
                confidence=min(1.0, 0.5 + (len(grouped) / max(threshold * 2, 1)) * 0.4),
                ambiguity=max(0.0, 1.0 - min(1.0, len(grouped) / max(threshold * 2, 1))),
                sensitivity_class=sensitivity,
            )
        )
    return observations


def _classify_sensitivity(events: Sequence[Mapping[str, Any]]) -> SensitivityClass:
    tags = {str(e.get("sensitivity_tag", "")).lower() for e in events}
    if "privacy" in tags:
        return "privacy_sensitive"
    if "mission" in tags:
        return "mission_changing"
    if "affect" in tags:
        return "affect_driven"
    if "public" in tags:
        return "public"
    return "internal"


__all__ = ["DEFAULT_REPEAT_THRESHOLD", "FIXTURE_CLOCK", "detect_repeated_patterns"]
