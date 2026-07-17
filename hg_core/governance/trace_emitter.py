"""HG-GOV-TRACE v1 append-only trace emitter.

Phase 0 is evidence only. It emits canonical, hash-chained trace records and
validates them; it does not grant, deny, permit, dispatch, or enforce policy.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Dict, Iterable, Mapping, Optional

from hg_core.governance.canonical_hash import canonical_hash, trace_record_hash

SCHEMA = "hg-gov-trace"
SCHEMA_VERSION = "1.0"
TRACE_FILENAME = "governance_trace.jsonl"
DECISIONS = {"allow", "deny", "hold", "skip"}
LAYERS = {"safety", "governance", "workflow", "audit"}
GOVERNANCE_EVENTS = {
    "intent_received",
    "llm_draft_generated",
    "outbound_validated",
    "permit_bound",
    "publish_blocked",
    "publish_attempted",
    "publish_succeeded",
    "publish_failed",
    "duplicate_skipped",
    "consent_checked",
    "consent_denied",
}


class TraceValidationError(ValueError):
    """A trace record violates the HG-GOV-TRACE v1 contract."""


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def immutable_record(value: Any) -> Any:
    """Deep immutable JSON-compatible view for emitted trace records."""
    if isinstance(value, dict):
        return MappingProxyType({key: immutable_record(val) for key, val in value.items()})
    if isinstance(value, list):
        return tuple(immutable_record(item) for item in value)
    return value


def trace_enabled() -> bool:
    return os.environ.get("HG_GOV_TRACE_ENABLED", "0").strip() == "1"


def _read_last(path: Path) -> tuple[int, Optional[str]]:
    if not path.exists():
        return 0, None
    last: Optional[Mapping[str, Any]] = None
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                last = json.loads(line)
    if last is None:
        return 0, None
    return int(last["seq"]), str(last["event_hash"])


def _validate_record(record: Mapping[str, Any]) -> None:
    required = {
        "schema",
        "schema_version",
        "seq",
        "prev_hash",
        "event_hash",
        "ts",
        "run_id",
        "workflow_id",
        "layer",
        "component",
        "event",
        "decision",
        "reason_code",
        "actor",
        "subject",
        "inputs_digest",
        "outputs_digest",
        "external_calls",
        "summary",
        "metadata",
    }
    missing = sorted(required - set(record.keys()))
    if missing:
        raise TraceValidationError(f"missing required fields: {', '.join(missing)}")
    if set(record.keys()) != required:
        extra = sorted(set(record.keys()) - required)
        raise TraceValidationError(f"unknown fields: {', '.join(extra)}")
    if record["schema"] != SCHEMA or record["schema_version"] != SCHEMA_VERSION:
        raise TraceValidationError("unsupported trace schema")
    if not isinstance(record["seq"], int) or record["seq"] < 1:
        raise TraceValidationError("seq must be an integer >= 1")
    if record["layer"] not in LAYERS:
        raise TraceValidationError(f"unknown layer {record['layer']!r}")
    decision = record["decision"]
    if decision is not None and decision not in DECISIONS:
        raise TraceValidationError(f"unknown decision {decision!r}")
    if decision is not None and not str(record["summary"]).strip():
        raise TraceValidationError("decision records require a non-empty summary")
    if record["layer"] == "governance" and record["event"] not in GOVERNANCE_EVENTS:
        raise TraceValidationError(f"unknown governance event {record['event']!r}")
    if record["layer"] == "safety" and "formal_event" not in record["metadata"]:
        raise TraceValidationError("safety trace records require metadata.formal_event")
    if not isinstance(record["external_calls"], int) or record["external_calls"] < 0:
        raise TraceValidationError("external_calls must be a non-negative integer")
    if trace_record_hash(record) != record["event_hash"]:
        raise TraceValidationError("event_hash mismatch")


@dataclass(frozen=True)
class TraceValidationResult:
    ok: bool
    records: int
    tampered: bool = False
    incomplete: bool = False
    error: Optional[str] = None
    head_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "records": self.records,
            "tampered": self.tampered,
            "incomplete": self.incomplete,
            "error": self.error,
            "head_hash": self.head_hash,
        }


class TraceEmitter:
    """Append-only per-run trace emitter."""

    def __init__(
        self,
        path: Path,
        *,
        enabled: Optional[bool] = None,
        clock: Optional[Callable[[], str]] = None,
    ) -> None:
        self.path = Path(path)
        self.enabled = trace_enabled() if enabled is None else enabled
        self._clock = clock or _utcnow_iso

    @classmethod
    def for_run_dir(
        cls,
        run_dir: Path,
        *,
        enabled: Optional[bool] = None,
        clock: Optional[Callable[[], str]] = None,
    ) -> "TraceEmitter":
        return cls(Path(run_dir) / TRACE_FILENAME, enabled=enabled, clock=clock)

    def emit(
        self,
        *,
        run_id: str,
        workflow_id: str,
        layer: str,
        component: str,
        event: str,
        summary: str,
        decision: Optional[str] = None,
        reason_code: Optional[str] = None,
        actor: Optional[Mapping[str, str]] = None,
        subject: Optional[Mapping[str, Any]] = None,
        inputs: Optional[Any] = None,
        outputs: Optional[Any] = None,
        inputs_digest: Optional[str] = None,
        outputs_digest: Optional[str] = None,
        external_calls: int = 0,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> Optional[Mapping[str, Any]]:
        if not self.enabled:
            return None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        last_seq, prev_hash = _read_last(self.path)
        record: Dict[str, Any] = {
            "schema": SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "seq": last_seq + 1,
            "prev_hash": prev_hash,
            "event_hash": "",
            "ts": self._clock(),
            "run_id": run_id,
            "workflow_id": workflow_id,
            "layer": layer,
            "component": component,
            "event": event,
            "decision": decision,
            "reason_code": reason_code,
            "actor": dict(actor or {"type": "agent", "id": "agent0"}),
            "subject": dict(subject or {"type": "runtime_event"}),
            "inputs_digest": inputs_digest or canonical_hash(inputs if inputs is not None else {}),
            "outputs_digest": outputs_digest if outputs_digest is not None else (
                canonical_hash(outputs) if outputs is not None else None
            ),
            "external_calls": external_calls,
            "summary": summary,
            "metadata": dict(metadata or {}),
        }
        record["event_hash"] = trace_record_hash(record)
        _validate_record(record)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        return immutable_record(record)

    def validate_chain(self) -> TraceValidationResult:
        return validate_chain(self.path)


def iter_records(path: Path) -> Iterable[Dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def validate_chain(path: Path) -> TraceValidationResult:
    path = Path(path)
    if not path.exists():
        return TraceValidationResult(ok=False, records=0, incomplete=True, error="missing trace")
    expected_seq = 1
    expected_prev: Optional[str] = None
    head_hash: Optional[str] = None
    count = 0
    try:
        for record in iter_records(path):
            if record.get("seq") != expected_seq:
                return TraceValidationResult(
                    ok=False,
                    records=count,
                    tampered=True,
                    error=f"seq gap: expected {expected_seq}, got {record.get('seq')}",
                    head_hash=head_hash,
                )
            if record.get("prev_hash") != expected_prev:
                return TraceValidationResult(
                    ok=False,
                    records=count,
                    tampered=True,
                    error=f"broken link at seq {record.get('seq')}",
                    head_hash=head_hash,
                )
            _validate_record(record)
            expected_prev = record["event_hash"]
            head_hash = record["event_hash"]
            expected_seq += 1
            count += 1
    except (json.JSONDecodeError, TraceValidationError, OSError) as exc:
        return TraceValidationResult(
            ok=False,
            records=count,
            tampered=True,
            error=str(exc),
            head_hash=head_hash,
        )
    return TraceValidationResult(ok=True, records=count, head_hash=head_hash)


__all__ = [
    "SCHEMA",
    "SCHEMA_VERSION",
    "TRACE_FILENAME",
    "TraceEmitter",
    "TraceValidationError",
    "TraceValidationResult",
    "canonical_hash",
    "immutable_record",
    "trace_enabled",
    "validate_chain",
]
