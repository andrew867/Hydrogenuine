"""
RTC handler contract — the ONLY module a handler may import from hg_runtime.

Handlers receive immutable events plus a read-only world view and return event
drafts. They never mutate world state, never call other handlers, and never
touch the bus directly (BUS-U3, BUS-S1). The loop owns emission: drafts become
real events (seq, hashes, chain) only when the loop passes them to the bus.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Dict, Iterable, List, Mapping, Optional, Protocol, Sequence, runtime_checkable

Event = Mapping[str, Any]


class ContractViolation(Exception):
    """A handler returned something that is not a well-formed event draft."""


def draft(
    type: str,
    payload: Dict[str, Any],
    *,
    causal_parents: Sequence[str] = (),
    severity: Optional[int] = None,
) -> Dict[str, Any]:
    """Build an event draft. The loop turns drafts into chained events."""
    if not isinstance(type, str) or not type:
        raise ContractViolation("draft requires a non-empty type string")
    if not isinstance(payload, dict):
        raise ContractViolation(f"draft payload must be a dict, got {type_name(payload)}")
    if severity is not None and (not isinstance(severity, int) or not 0 <= severity <= 10):
        raise ContractViolation(f"draft severity must be None or int 0-10, got {severity!r}")
    return {
        "type": type,
        "payload": jsonable(payload),
        "causal_parents": list(jsonable(list(causal_parents))),
        "severity": severity,
    }


def type_name(obj: Any) -> str:
    return obj.__class__.__name__


def jsonable(value: Any) -> Any:
    """Copy read-only handler inputs back into JSON-compatible draft values."""
    if isinstance(value, Mapping):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    return value


_DRAFT_KEYS = {"type", "payload", "causal_parents", "severity"}


def validate_drafts(drafts: Any, handler_id: str) -> List[Dict[str, Any]]:
    """Validate a handler's return value: a list of drafts, nothing else."""
    if drafts is None:
        return []
    if not isinstance(drafts, (list, tuple)):
        raise ContractViolation(
            f"handler {handler_id!r} must return a list of event drafts, got {type_name(drafts)}"
        )
    out: List[Dict[str, Any]] = []
    for d in drafts:
        if not isinstance(d, dict) or set(d.keys()) != _DRAFT_KEYS:
            raise ContractViolation(
                f"handler {handler_id!r} returned a non-draft item: {d!r}"
            )
        out.append(d)
    return out


def readonly_view(obj: Any) -> Any:
    """
    Deep read-only view over dict/list structures. Handlers receive world state
    only through this — direct mutation raises TypeError at the call site.
    """
    if isinstance(obj, dict):
        return MappingProxyType({k: readonly_view(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return tuple(readonly_view(v) for v in obj)
    return obj


@runtime_checkable
class CognitionHandler(Protocol):
    """Step 6 — proposes via events; zero tool handles (INV-A32)."""

    handler_id: str

    def propose(self, context: Mapping[str, Any]) -> List[Dict[str, Any]]:
        """Return PROPOSAL_* drafts for the given context."""
        ...

    def halt(self) -> None:
        """PANIC step 0: stop any in-flight generation."""
        ...


@runtime_checkable
class DecisionHandler(Protocol):
    """Step 7 — SOAR/HAL/GPP pipeline; proposals in, decision events out."""

    handler_id: str

    def evaluate(
        self,
        events: Sequence[Event],
        proposals: Sequence[Event],
        view: Mapping[str, Any],
        aep_state: Mapping[str, Any],
    ) -> List[Dict[str, Any]]:
        ...


@runtime_checkable
class KernelHandler(Protocol):
    """Step 8 — sole execution gate; OEA dispatch happens inside (INV-A28)."""

    handler_id: str

    def execute(
        self, decisions: Sequence[Event], view: Mapping[str, Any]
    ) -> List[Dict[str, Any]]:
        ...

    def block_all(self) -> None:
        """PANIC step 0: refuse all externalization until cleared."""
        ...

    def unblock(self) -> None:
        ...


@runtime_checkable
class MemoryHandler(Protocol):
    """Steps 5 and 10 — retrieval with provenance; evented write-back."""

    handler_id: str

    def retrieve(
        self, view: Mapping[str, Any], events: Sequence[Event]
    ) -> Mapping[str, Any]:
        """Return {"context": ..., "provenance": {"query": ..., "result_refs": [...]}}."""
        ...

    def store(
        self,
        events: Sequence[Event],
        proposals: Sequence[Event],
        results: Sequence[Event],
    ) -> List[Dict[str, Any]]:
        ...


@runtime_checkable
class ArousalReader(Protocol):
    """Step 3 — modulation only; the returned state carries no authority."""

    handler_id: str

    def read(
        self, events: Sequence[Event], view: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        """Return {"max_severity": int, "dimensions": {name: severity}}."""
        ...


@runtime_checkable
class RecoveryHandler(Protocol):
    """Step 4 — CRR; may pause the tick, never touches authority or evidence."""

    handler_id: str

    def should_enter_cycle(
        self, view: Mapping[str, Any], aep_state: Mapping[str, Any]
    ) -> bool:
        ...

    def execute_cycle(self) -> List[Dict[str, Any]]:
        """Run the cycle; return RECOVERY_STATE_CHANGED drafts."""
        ...

    def enter_safe_state(self) -> None:
        """PANIC step 0."""
        ...


@runtime_checkable
class YawnHandler(Protocol):
    """Step 4a — YSR; soft posture reset only; never touches authority or evidence."""

    handler_id: str

    def should_yawn(
        self,
        view: Mapping[str, Any],
        aep_state: Mapping[str, Any],
        *,
        panic_active: bool = False,
        operator_requested: bool = False,
    ) -> bool:
        ...

    def execute_yawn(
        self,
        view: Mapping[str, Any],
        aep_state: Mapping[str, Any],
        *,
        panic_active: bool = False,
        operator_requested: bool = False,
    ) -> List[Dict[str, Any]]:
        """Return YSR_* observation drafts only."""
        ...

    def bind_runtime(self, bus: Any, state: Mapping[str, Any]) -> None:
        ...


@runtime_checkable
class MeditationHandler(Protocol):
    """Step 4b — MSC; quiet observation only; never touches authority or execution."""

    handler_id: str

    def should_enter_cycle(
        self,
        view: Mapping[str, Any],
        aep_state: Mapping[str, Any],
        *,
        panic_active: bool = False,
        operator_requested: bool = False,
    ) -> bool:
        ...

    def execute_cycle(
        self,
        view: Mapping[str, Any],
        aep_state: Mapping[str, Any],
        *,
        panic_active: bool = False,
    ) -> List[Dict[str, Any]]:
        """Return MSC_* observation drafts only."""
        ...

    def bind_runtime(self, bus: Any, state: Mapping[str, Any]) -> None:
        ...


def stable_id(prefix: str, *parts: Any) -> str:
    """Deterministic id helper for handlers (no clock, no randomness — replayable)."""
    import hashlib

    h = hashlib.sha256("\x1f".join(str(p) for p in parts).encode("utf-8")).hexdigest()
    return f"{prefix}_{h[:16]}"


__all__ = [
    "Event",
    "ContractViolation",
    "draft",
    "validate_drafts",
    "readonly_view",
    "stable_id",
    "CognitionHandler",
    "DecisionHandler",
    "KernelHandler",
    "MemoryHandler",
    "ArousalReader",
    "RecoveryHandler",
    "MeditationHandler",
    "YawnHandler",
]
