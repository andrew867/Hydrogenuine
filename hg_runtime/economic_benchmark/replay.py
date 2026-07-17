"""Append-only economic-benchmark record log with deterministic replay.

Benchmark records (suites, cases, outcomes, verifications, receipts) are hash-chained
so the run is reproducible and any tampering fails replay. Replay divergence is a
failure, not a warning.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.economic_benchmark.schemas import EconomicBenchmarkError, preempt_if_needed

GENESIS_HASH = "sha256:phase34_genesis"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _immutable(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _immutable(val) for key, val in value.items()})
    if isinstance(value, list):
        return tuple(_immutable(item) for item in value)
    return value


def _plain(value: Any) -> Any:
    if isinstance(value, (MappingProxyType, dict)):
        return {key: _plain(val) for key, val in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def _record_hash(record: Mapping[str, Any]) -> str:
    return canonical_hash({key: value for key, value in record.items() if key != "chain_hash"})


@dataclass(frozen=True)
class BenchmarkRecord:
    record_id: str
    schema: str
    created_at: str
    payload: Mapping[str, Any]
    payload_hash: str
    previous_hash: str
    chain_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "schema": self.schema,
            "created_at": self.created_at,
            "payload": _plain(self.payload),
            "payload_hash": self.payload_hash,
            "previous_hash": self.previous_hash,
            "chain_hash": self.chain_hash,
        }


@dataclass(frozen=True)
class BenchmarkReplayResult:
    ok: bool
    records: int
    chain_root: str | None
    errors: list[str]


class EconomicBenchmarkLog:
    """Append-only JSONL log of benchmark records, hash-chained for replay."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._head_hash = self._load_head()

    def _load_head(self) -> str | None:
        head: str | None = None
        for record in self.iter_records():
            head = record.chain_hash
        return head

    def append(self, schema: str, payload: Mapping[str, Any], *, created_at: str | None = None, control=None) -> BenchmarkRecord:
        preempt_if_needed(control)
        previous = self._head_hash or GENESIS_HASH
        enriched = dict(payload)
        payload_hash = canonical_hash(enriched)
        base = {
            "record_id": "eb-" + canonical_hash({"schema": schema, "payload_hash": payload_hash, "previous": previous}).removeprefix("sha256:")[:20],
            "schema": schema,
            "created_at": created_at or _utc_now(),
            "payload": enriched,
            "payload_hash": payload_hash,
            "previous_hash": previous,
        }
        base["chain_hash"] = _record_hash(base)
        record = BenchmarkRecord(
            record_id=base["record_id"],
            schema=base["schema"],
            created_at=base["created_at"],
            payload=_immutable(base["payload"]),
            payload_hash=base["payload_hash"],
            previous_hash=base["previous_hash"],
            chain_hash=base["chain_hash"],
        )
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        self._head_hash = record.chain_hash
        return record

    def iter_records(self) -> list[BenchmarkRecord]:
        if not self.path.exists():
            return []
        records: list[BenchmarkRecord] = []
        with self.path.open("r", encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                data = json.loads(line)
                records.append(
                    BenchmarkRecord(
                        record_id=data["record_id"],
                        schema=data["schema"],
                        created_at=data["created_at"],
                        payload=_immutable(data["payload"]),
                        payload_hash=data["payload_hash"],
                        previous_hash=data["previous_hash"],
                        chain_hash=data["chain_hash"],
                    )
                )
        return records

    def replay(self, *, control: OperationControl | None = None) -> BenchmarkReplayResult:
        preempt_if_needed(control, stop_blocks=False)
        errors: list[str] = []
        previous = GENESIS_HASH
        head: str | None = None
        count = 0
        for record in self.iter_records():
            data = record.to_dict()
            if data["previous_hash"] != previous:
                errors.append(f"chain_break:{record.record_id}")
            if canonical_hash(data["payload"]) != data["payload_hash"]:
                errors.append(f"payload_hash_mismatch:{record.record_id}")
            if _record_hash(data) != data["chain_hash"]:
                errors.append(f"chain_hash_mismatch:{record.record_id}")
            previous = data["chain_hash"]
            head = previous
            count += 1
        return BenchmarkReplayResult(ok=not errors, records=count, chain_root=head, errors=errors)


def enforce_dry_live_boundary(*, live: bool, operator_permit_refs: list[str] | None = None) -> str:
    """A benchmark run is dry by default; a live run requires operator permits."""
    if not live:
        return "dry"
    if not (operator_permit_refs or []):
        raise EconomicBenchmarkError("dry_live_boundary_enforced:live_benchmark_requires_operator_permit")
    return "live"


__all__ = [
    "GENESIS_HASH",
    "BenchmarkRecord",
    "BenchmarkReplayResult",
    "EconomicBenchmarkLog",
    "enforce_dry_live_boundary",
]
