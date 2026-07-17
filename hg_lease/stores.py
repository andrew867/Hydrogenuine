"""Four-store separation: context, lease, situation, receipts.

Each store has its own schema and API. The context store structurally cannot
hold authority (`authority` is always NONE and validation rejects anything
else). The receipt store is append-only with a verifiable hash chain;
corrections are appended, never rewritten.

Persistence is local-first: in-memory with optional JSON-lines append files.
No store performs any network I/O.
"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from hg_core.governance.canonical_hash import canonical_hash

from hg_lease.lease import CapabilityLease, LifecycleEvent


class StoreValidationError(ValueError):
    """Rejected record — fail closed."""


# ---------------------------------------------------------------- context ---

CONTEXT_SCHEMA_VERSION = "hg.context.v1"
_CONTEXT_SOURCES = {"EXPLICIT_OPERATOR", "INFERRED_SUMMARY", "IMPORTED"}
_CONTEXT_CONFIDENCE = {"EXPLICIT", "HIGH", "MEDIUM", "LOW"}


@dataclass(frozen=True)
class ContextRecord:
    context_id: str
    subject: str
    statement: str
    source: str
    confidence: str
    recorded_at: str
    structured_meaning: dict[str, Any] = field(default_factory=dict)
    valid_until: Optional[str] = None
    supersedes: Optional[str] = None
    retention_class: str = "default"
    authority: str = "NONE"

    def __post_init__(self) -> None:
        if self.authority != "NONE":
            raise StoreValidationError(
                "context records can never carry authority (authority must be NONE)"
            )
        if self.source not in _CONTEXT_SOURCES:
            raise StoreValidationError(f"invalid context source: {self.source!r}")
        if self.confidence not in _CONTEXT_CONFIDENCE:
            raise StoreValidationError(f"invalid confidence: {self.confidence!r}")

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": CONTEXT_SCHEMA_VERSION,
            "context_id": self.context_id,
            "subject": self.subject,
            "statement": self.statement,
            "structured_meaning": dict(self.structured_meaning),
            "source": self.source,
            "confidence": self.confidence,
            "recorded_at": self.recorded_at,
            "valid_until": self.valid_until,
            "supersedes": self.supersedes,
            "retention_class": self.retention_class,
            "authority": "NONE",
        }


class ContextStore:
    """Remembered statements. Citable during drafting; never a lease."""

    def __init__(self) -> None:
        self._records: dict[str, ContextRecord] = {}
        self._lock = threading.Lock()

    def put(self, record: ContextRecord) -> None:
        payload = record.to_payload()
        if payload.get("authority") != "NONE":
            raise StoreValidationError("context authority must be NONE")
        with self._lock:
            self._records[record.context_id] = record

    def get(self, context_id: str) -> Optional[ContextRecord]:
        return self._records.get(context_id)

    def for_subject(self, subject: str) -> list[ContextRecord]:
        return [r for r in self._records.values() if r.subject == subject]

    def export(self) -> list[dict[str, Any]]:
        return [r.to_payload() for r in self._records.values()]

    def delete_subject(self, subject: str) -> int:
        """Local privacy control: delete all context for a subject."""
        with self._lock:
            doomed = [cid for cid, r in self._records.items() if r.subject == subject]
            for cid in doomed:
                del self._records[cid]
        return len(doomed)

    def purge_retention_class(self, retention_class: str) -> int:
        with self._lock:
            doomed = [
                cid for cid, r in self._records.items()
                if r.retention_class == retention_class
            ]
            for cid in doomed:
                del self._records[cid]
        return len(doomed)


# -------------------------------------------------------------- situation ---

FACT_SCHEMA_VERSION = "hg.fact.v1"


@dataclass(frozen=True)
class SituationFact:
    name: str
    typed_value: Any
    observed_at: str
    source_id: str
    unit: Optional[str] = None
    expires_at: Optional[str] = None
    source_trust: int = 0
    fact_id: str = field(default_factory=lambda: f"fact_{uuid.uuid4().hex[:12]}")

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": FACT_SCHEMA_VERSION,
            "fact_id": self.fact_id,
            "name": self.name,
            "typed_value": self.typed_value,
            "unit": self.unit,
            "source_id": self.source_id,
            "source_trust": self.source_trust,
            "observed_at": self.observed_at,
            "expires_at": self.expires_at,
        }


class SituationStore:
    """Current environmental and system facts used for policy evaluation."""

    def __init__(self) -> None:
        self._facts: dict[str, SituationFact] = {}
        self._lock = threading.Lock()
        self._listeners: list[Callable[[SituationFact, Optional[SituationFact]], None]] = []

    def subscribe(
        self, listener: Callable[[SituationFact, Optional[SituationFact]], None]
    ) -> None:
        self._listeners.append(listener)

    def put(self, fact: SituationFact) -> None:
        with self._lock:
            previous = self._facts.get(fact.name)
            self._facts[fact.name] = fact
        for listener in list(self._listeners):
            listener(fact, previous)

    def get(self, name: str) -> Optional[SituationFact]:
        return self._facts.get(name)

    def snapshot(self, *, now_wall: str) -> dict[str, SituationFact]:
        """Unexpired facts by name. Expired facts are excluded so that
        conditions over them fail closed as unknown/stale."""
        with self._lock:
            return {
                name: fact
                for name, fact in self._facts.items()
                if fact.expires_at is None or str(fact.expires_at) > now_wall
            }

    @staticmethod
    def snapshot_hash(snapshot: dict[str, SituationFact]) -> str:
        return canonical_hash(
            {name: fact.to_payload() for name, fact in sorted(snapshot.items())}
        )


# ------------------------------------------------------------------ lease ---


class LeaseStore:
    """Authority-bearing store. Only lease records; no context, no receipts."""

    def __init__(self) -> None:
        self._leases: dict[str, CapabilityLease] = {}
        self._events: list[LifecycleEvent] = []
        self._lock = threading.Lock()

    def put(self, lease: CapabilityLease, event: Optional[LifecycleEvent] = None) -> None:
        with self._lock:
            self._leases[lease.lease_id] = lease
            if event is not None:
                self._events.append(event)

    def get(self, lease_id: str) -> Optional[CapabilityLease]:
        return self._leases.get(lease_id)

    def all(self) -> list[CapabilityLease]:
        return list(self._leases.values())

    def active(self) -> list[CapabilityLease]:
        return [l for l in self._leases.values() if l.state == "ACTIVE"]

    def active_for(self, *, subject: str, action_type: str, object_id: str) -> list[CapabilityLease]:
        return [
            l
            for l in self.active()
            if l.subject == subject
            and action_type in l.action_scope
            and object_id in l.object_scope
        ]

    def events(self) -> list[LifecycleEvent]:
        return list(self._events)


# ---------------------------------------------------------------- receipt ---

RECEIPT_SCHEMA_VERSION = "hg.receipt.v1"


class ReceiptStore:
    """Append-only receipt chain. No update or delete API exists.

    Each receipt embeds the previous receipt's hash; `verify_chain` recomputes
    every hash. Corrections reference the corrected receipt via
    `correction_of` and are appended like any other receipt.
    """

    def __init__(self, journal_path: Optional[Path] = None) -> None:
        self._receipts: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._journal_path = journal_path

    def append(
        self,
        *,
        decision_id: str,
        outcome: str,
        attempted_at: str,
        situation_snapshot_hash: str,
        lease_hash: Optional[str] = None,
        policy_hash: Optional[str] = None,
        adapter_request_hash: Optional[str] = None,
        adapter_result_hash: Optional[str] = None,
        completed_at: Optional[str] = None,
        correction_of: Optional[str] = None,
        detail: str = "",
    ) -> dict[str, Any]:
        with self._lock:
            previous_hash = self._receipts[-1]["receipt_hash"] if self._receipts else None
            body = {
                "schema_version": RECEIPT_SCHEMA_VERSION,
                "receipt_id": f"rcpt_{uuid.uuid4().hex[:16]}",
                "previous_receipt_hash": previous_hash,
                "decision_id": decision_id,
                "lease_hash": lease_hash,
                "policy_hash": policy_hash,
                "situation_snapshot_hash": situation_snapshot_hash,
                "adapter_request_hash": adapter_request_hash,
                "adapter_result_hash": adapter_result_hash,
                "attempted_at": attempted_at,
                "completed_at": completed_at,
                "outcome": outcome,
                "correction_of": correction_of,
                "detail": detail,
            }
            body["receipt_hash"] = canonical_hash(
                {k: v for k, v in body.items() if k != "receipt_hash"}
            )
            self._receipts.append(body)
            if self._journal_path is not None:
                with open(self._journal_path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(body) + "\n")
            return dict(body)

    def all(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self._receipts]

    def get(self, receipt_id: str) -> Optional[dict[str, Any]]:
        for r in self._receipts:
            if r["receipt_id"] == receipt_id:
                return dict(r)
        return None

    def verify_chain(self) -> bool:
        previous_hash = None
        for r in self._receipts:
            if r["previous_receipt_hash"] != previous_hash:
                return False
            recomputed = canonical_hash(
                {k: v for k, v in r.items() if k != "receipt_hash"}
            )
            if recomputed != r["receipt_hash"]:
                return False
            previous_hash = r["receipt_hash"]
        return True
