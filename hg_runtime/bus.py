"""
RTC event bus — the spine (RTC_EVENT_BUS_SPEC.md).

One immutable, strictly seq-ordered, hash-chained JSONL stream under
memory/runtime/. Daily segments; the chain carries across rotation. Typed
against hg_runtime/event_types_v1.yaml — unknown types are rejected at emit.

Canonical hashing reuses hg_core.ledger.canonical_json (INV-A27: one canonical
JSON definition in the codebase, not two).
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Dict, Iterator, List, Mapping, Optional, Sequence, Tuple

import yaml

from hg_core.ledger.canonical_json import canonical_dumps
from hg_core.secrets.events import SecretEmissionRefused, guard_event_payload

GENESIS_HASH = "sha256:genesis"
SEGMENT_PREFIX = "events-"
SEGMENT_SUFFIX = ".jsonl"
DEFAULT_QUEUE_CAPACITY = 256


class BusError(Exception):
    """Emit-time validation failure (bad type, bad draft) — never silent."""


class BusWriteError(Exception):
    """Durable append failed. The spine must not lie: the loop treats this as fatal."""


class ChainError(Exception):
    """Chain verification failure: tamper, gap, or broken link."""


# ---------------------------------------------------------------------------
# Type registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EventTypeInfo:
    family: str
    priority: int
    cognition_eligible: bool


class TypeRegistry:
    """Versioned event vocabulary. Adding a type = a commit to the YAML."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else Path(__file__).parent / "event_types_v1.yaml"
        raw_bytes = self.path.read_bytes()
        self.registry_hash = "sha256:" + hashlib.sha256(raw_bytes).hexdigest()
        data = yaml.safe_load(raw_bytes)
        if not isinstance(data, dict) or "types" not in data:
            raise BusError(f"malformed type registry: {self.path}")
        self.version = str(data.get("version", "unknown"))
        self._types: Dict[str, EventTypeInfo] = {}
        for name, spec in data["types"].items():
            self._types[name] = EventTypeInfo(
                family=str(spec["family"]),
                priority=int(spec["priority"]),
                cognition_eligible=bool(spec["cognition_eligible"]),
            )

    def __contains__(self, type_name: str) -> bool:
        return type_name in self._types

    def info(self, type_name: str) -> EventTypeInfo:
        try:
            return self._types[type_name]
        except KeyError:
            raise BusError(f"unknown event type {type_name!r} — not in registry {self.path.name}")

    def cognition_eligible(self, type_name: str) -> bool:
        return type_name in self._types and self._types[type_name].cognition_eligible


# ---------------------------------------------------------------------------
# Envelope construction
# ---------------------------------------------------------------------------


def compute_event_hash(envelope_without_hash: Dict[str, Any]) -> str:
    """sha256 over canonical JSON of the envelope minus event_hash/event_id."""
    body = {k: v for k, v in envelope_without_hash.items() if k not in ("event_hash", "event_id")}
    return "sha256:" + hashlib.sha256(canonical_dumps(body)).hexdigest()


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def immutable_event(value: Any) -> Any:
    """Deep immutable JSON-compatible view for live emitted events."""
    if isinstance(value, dict):
        return MappingProxyType({k: immutable_event(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(immutable_event(v) for v in value)
    return value


@dataclass(order=True)
class _QueuedDraft:
    sort_key: Tuple[int, int] = field(compare=True)  # (-priority, arrival)
    draft: Dict[str, Any] = field(compare=False, default_factory=dict)
    source: str = field(compare=False, default="")


class EventBus:
    """
    The single ordered stream. `emit` is the only way an event becomes real;
    `submit` is the bounded ingress queue for external sources; `poll` is the
    loop's blocking drain. Replay reads via `read_all`.
    """

    def __init__(
        self,
        root: Path,
        registry: Optional[TypeRegistry] = None,
        clock: Optional[Callable[[], str]] = None,
        queue_capacity: int = DEFAULT_QUEUE_CAPACITY,
    ) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.registry = registry or TypeRegistry()
        self._clock = clock or _utcnow_iso
        self._queue_capacity = queue_capacity
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)
        self._queue: List[_QueuedDraft] = []
        self._arrival_counter = 0
        self._dropped_pending: Dict[str, int] = {}  # type -> count since last report
        self._quarantined: set = set()
        self.next_seq, self.head_hash = self._recover_chain_head()

    # -- chain head recovery ------------------------------------------------

    def _segments(self) -> List[Path]:
        return sorted(self.root.glob(f"{SEGMENT_PREFIX}*{SEGMENT_SUFFIX}"))

    def _recover_chain_head(self) -> Tuple[int, str]:
        segments = self._segments()
        if not segments:
            return 0, GENESIS_HASH
        last_line: Optional[str] = None
        with segments[-1].open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    last_line = line
        if last_line is None:
            # Empty trailing segment: fall back to scanning the previous one.
            for seg in reversed(segments[:-1]):
                with seg.open("r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            last_line = line
                if last_line:
                    break
        if last_line is None:
            return 0, GENESIS_HASH
        last = json.loads(last_line)
        return int(last["seq"]) + 1, str(last["event_hash"])

    def _segment_for(self, timestamp: str) -> Path:
        day = timestamp[:10].replace("-", "")
        return self.root / f"{SEGMENT_PREFIX}{day}{SEGMENT_SUFFIX}"

    # -- emit ----------------------------------------------------------------

    def emit(
        self,
        type: str,
        payload: Dict[str, Any],
        source: str,
        causal_parents: Sequence[str] = (),
        severity: Optional[int] = None,
    ) -> Mapping[str, Any]:
        """Validate, chain, durably append, return the full event."""
        info = self.registry.info(type)  # raises BusError on unknown type
        if not isinstance(payload, dict):
            raise BusError(f"payload must be a dict for {type}, got {payload.__class__.__name__}")
        try:
            guard_event_payload(payload)
        except SecretEmissionRefused as exc:
            raise BusError(f"secret_emission_refused:{exc.reason}") from exc
        with self._lock:
            envelope: Dict[str, Any] = {
                "schema": "rtc-event",
                "schema_version": "1.0",
                "seq": self.next_seq,
                "timestamp": self._clock(),
                "type": type,
                "payload": payload,
                "source": source,
                "causal_parents": list(causal_parents),
                "severity": severity,
                "prev_hash": self.head_hash,
            }
            event_hash = compute_event_hash(envelope)
            envelope["event_hash"] = event_hash
            envelope["event_id"] = "evt_" + event_hash[len("sha256:"):][:16]
            self._append(envelope)
            self.next_seq += 1
            self.head_hash = event_hash
            return immutable_event(envelope)

    def emit_draft(self, d: Dict[str, Any], source: str) -> Mapping[str, Any]:
        return self.emit(
            d["type"],
            d["payload"],
            source,
            causal_parents=d.get("causal_parents") or (),
            severity=d.get("severity"),
        )

    def _append(self, envelope: Dict[str, Any]) -> None:
        path = self._segment_for(envelope["timestamp"])
        line = json.dumps(envelope, ensure_ascii=False, sort_keys=True) + "\n"
        try:
            with path.open("a", encoding="utf-8") as f:
                f.write(line)
                f.flush()
                os.fsync(f.fileno())
        except OSError as exc:
            raise BusWriteError(f"bus append failed at seq {envelope['seq']}: {exc}") from exc

    # -- ingress queue ---------------------------------------------------------

    def submit(
        self,
        type: str,
        payload: Dict[str, Any],
        source: str,
        causal_parents: Sequence[str] = (),
        severity: Optional[int] = None,
    ) -> bool:
        """
        Enqueue an ingress draft (bounded). Overflow drops the oldest
        lowest-priority entry and counts it — the next poll reports
        EVENTS_DROPPED on the stream. Returns False if this submission itself
        was the one dropped.
        """
        info = self.registry.info(type)
        with self._not_empty:
            self._arrival_counter += 1
            item = _QueuedDraft(
                sort_key=(-info.priority, self._arrival_counter),
                draft={
                    "type": type,
                    "payload": payload,
                    "causal_parents": list(causal_parents),
                    "severity": severity,
                },
                source=source,
            )
            self._queue.append(item)
            accepted = True
            if len(self._queue) > self._queue_capacity:
                # Drop the lowest-priority entry; among equals, the oldest.
                # sort_key = (-priority, arrival): lowest priority maximizes
                # sort_key[0]; oldest minimizes arrival.
                victim_idx = max(
                    range(len(self._queue)),
                    key=lambda i: (self._queue[i].sort_key[0], -self._queue[i].sort_key[1]),
                )
                victim = self._queue.pop(victim_idx)
                vtype = victim.draft["type"]
                self._dropped_pending[vtype] = self._dropped_pending.get(vtype, 0) + 1
                accepted = victim is not item
            self._not_empty.notify()
            return accepted

    def poll(self, timeout: float) -> List[Mapping[str, Any]]:
        """
        Block until ingress is available or timeout. Drains the queue in
        arrival order, durably emits each draft, and returns the emitted
        events. Pending drop counts are reported first (never silent).
        Timeout returns [] — idleness emits nothing.
        """
        with self._not_empty:
            if not self._queue and not self._dropped_pending:
                self._not_empty.wait(timeout=timeout)
            if not self._queue and not self._dropped_pending:
                return []
            batch = sorted(self._queue, key=lambda q: q.sort_key[1])
            self._queue.clear()
            dropped = dict(self._dropped_pending)
            self._dropped_pending.clear()
        events: List[Mapping[str, Any]] = []
        if dropped:
            events.append(
                self.emit(
                    "EVENTS_DROPPED",
                    {"dropped": dropped, "total": sum(dropped.values())},
                    source="loop",
                )
            )
        for item in batch:
            events.append(self.emit_draft(item.draft, item.source))
        return events

    # -- quarantine -------------------------------------------------------------

    def quarantine(self, event: Dict[str, Any], handler_id: str, error: str) -> None:
        """Park a poison event after N failed deliveries; the loop never dies on it."""
        record = {
            "event_id": event["event_id"],
            "seq": event["seq"],
            "type": event["type"],
            "handler_id": handler_id,
            "error": error[:2000],
            "quarantined_at": self._clock(),
        }
        path = self.root / "quarantine.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())
        self._quarantined.add(event["event_id"])

    def is_quarantined(self, event_id: str) -> bool:
        return event_id in self._quarantined

    # -- read / verify ------------------------------------------------------------

    def read_all(self) -> Iterator[Dict[str, Any]]:
        """All events across segments in seq order (the replay source)."""
        for seg in self._segments():
            with seg.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        yield json.loads(line)

    def verify_chain(self) -> Dict[str, Any]:
        """
        Recompute every hash and link across all segments (rotation included).
        Returns {"ok": bool, "events": n, "error": ...} — raises nothing so
        gates can report cleanly.
        """
        expected_seq = 0
        expected_prev = GENESIS_HASH
        count = 0
        for event in self.read_all():
            if event["seq"] != expected_seq:
                return {"ok": False, "events": count,
                        "error": f"seq gap: expected {expected_seq}, got {event['seq']}"}
            if event["prev_hash"] != expected_prev:
                return {"ok": False, "events": count,
                        "error": f"broken link at seq {event['seq']}"}
            recomputed = compute_event_hash(event)
            if recomputed != event["event_hash"]:
                return {"ok": False, "events": count,
                        "error": f"hash mismatch at seq {event['seq']} (tamper)"}
            expected_prev = event["event_hash"]
            expected_seq += 1
            count += 1
        return {"ok": True, "events": count, "error": None}


__all__ = [
    "EventBus",
    "TypeRegistry",
    "EventTypeInfo",
    "BusError",
    "BusWriteError",
    "ChainError",
    "GENESIS_HASH",
    "compute_event_hash",
    "immutable_event",
]
