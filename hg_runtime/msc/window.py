"""Bounded RTC event window selection for MSC listening."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

from hg_runtime.memory.types import redact_mapping

SECRET_EXCLUDE_TYPES = frozenset(
    {
        "TER_COMMAND_COMPLETED",
        "TER_COMMAND_STARTED",
    }
)

HUGE_PAYLOAD_KEYS = frozenset({"stdout", "stderr", "output", "raw_output", "body"})


def _parse_ts(ts: str) -> datetime | None:
    try:
        if ts.endswith("Z"):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def _event_hash(event: Mapping[str, Any]) -> str:
    eid = str(event.get("event_id", ""))
    digest = hashlib.sha256(eid.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _subsystem_from_type(etype: str) -> str:
    if etype.startswith("AEP_"):
        return "aep"
    if etype.startswith("CRR_") or etype == "RECOVERY_STATE_CHANGED":
        return "crr"
    if etype.startswith("OEA_"):
        return "oea"
    if etype.startswith("TER_"):
        return "ter"
    if etype.startswith("UEAK_"):
        return "ueak"
    if etype.startswith("GPP_"):
        return "gpp"
    if etype.startswith("SRP_"):
        return "srp"
    if etype.startswith("CSM_"):
        return "csm"
    if etype.startswith("MEL_"):
        return "mel"
    if etype.startswith("MEMORY_"):
        return "memory"
    if etype.startswith("MSC_"):
        return "msc"
    if etype.startswith("MODEL_") or etype.startswith("PROPOSAL_"):
        return "cognition"
    if etype.startswith("DECISION_") or etype.startswith("HAL_") or etype.startswith("SOAR_"):
        return "decision"
    return "other"


def _redact_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    redacted = redact_mapping(dict(payload))
    for key in HUGE_PAYLOAD_KEYS:
        if key in redacted and isinstance(redacted[key], str) and len(redacted[key]) > 256:
            redacted[key] = f"[TRUNCATED:{len(redacted[key])}]"
    return redacted


@dataclass(frozen=True)
class EventWindowSelection:
    agent_id: str
    window_id: str
    event_ids: tuple[str, ...]
    event_hashes: tuple[str, ...]
    seq_start: int | None
    seq_end: int | None
    observed_subsystems: tuple[str, ...]
    redacted_count: int
    excluded_count: int

    def to_payload(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "window_id": self.window_id,
            "event_ids": list(self.event_ids),
            "event_hashes": list(self.event_hashes),
            "seq_start": self.seq_start,
            "seq_end": self.seq_end,
            "observed_subsystems": list(self.observed_subsystems),
            "redacted_count": self.redacted_count,
            "excluded_count": self.excluded_count,
        }


def select_bounded_window(
    events: Sequence[Mapping[str, Any]],
    *,
    agent_id: str,
    window_id: str,
    max_events: int,
    max_age_seconds: int,
    clock_now: str,
    subsystem_filters: Iterable[str] | None = None,
    exclude_types: Iterable[str] | None = None,
) -> EventWindowSelection:
    """Select a bounded, redacted event window from the tail of the log."""
    filters = set(subsystem_filters or ())
    if "rtc" in filters:
        filters = set()
    excluded = set(exclude_types or ()) | SECRET_EXCLUDE_TYPES
    now = _parse_ts(clock_now)

    candidates: list[Mapping[str, Any]] = []
    for event in reversed(list(events)):
        etype = str(event.get("type", ""))
        if etype in excluded:
            continue
        subsystem = _subsystem_from_type(etype)
        if filters and subsystem not in filters:
            continue
        if now is not None and max_age_seconds > 0:
            ets = _parse_ts(str(event.get("timestamp", "")))
            if ets is not None and (now - ets).total_seconds() > max_age_seconds:
                continue
        candidates.append(event)
        if len(candidates) >= max_events:
            break

    selected = list(reversed(candidates))
    event_ids: list[str] = []
    event_hashes: list[str] = []
    subsystems: set[str] = set()
    redacted = 0
    excluded_count = 0

    for event in selected:
        etype = str(event.get("type", ""))
        if etype in excluded:
            excluded_count += 1
            continue
        payload = event.get("payload", {})
        if isinstance(payload, Mapping):
            cleaned = _redact_payload(payload)
            if cleaned != dict(payload):
                redacted += 1
        event_ids.append(str(event["event_id"]))
        event_hashes.append(_event_hash(event))
        subsystems.add(_subsystem_from_type(etype))

    seqs = [int(e["seq"]) for e in selected if "seq" in e]
    return EventWindowSelection(
        agent_id=agent_id,
        window_id=window_id,
        event_ids=tuple(event_ids),
        event_hashes=tuple(event_hashes),
        seq_start=min(seqs) if seqs else None,
        seq_end=max(seqs) if seqs else None,
        observed_subsystems=tuple(sorted(subsystems)),
        redacted_count=redacted,
        excluded_count=excluded_count,
    )


__all__ = ["EventWindowSelection", "select_bounded_window", "_subsystem_from_type"]
