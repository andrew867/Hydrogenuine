"""Phase 39 in-memory receipt chain.

A hash-chained event recorder used by the loop so a soak can run without touching
the filesystem and still produce a verifiable receipt chain. The chain algorithm
is byte-identical to :class:`StabilityLog`, so records flushed to disk replay to
the same root. Recording an event never grants authority or creates an effect.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.long_run_stability.replay import GENESIS_HASH


class ReceiptChain:
    def __init__(self, head: str | None = None, records: list[dict[str, Any]] | None = None) -> None:
        self.records: list[dict[str, Any]] = list(records or [])
        self.head = head or (self.records[-1]["chain_hash"] if self.records else GENESIS_HASH)

    def append(self, schema: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        record = {
            "schema": schema,
            "payload": dict(payload),
            "payload_hash": canonical_hash(dict(payload)),
            "previous_hash": self.head,
        }
        record["record_id"] = "p39-" + canonical_hash(record).removeprefix("sha256:")[:20]
        record["chain_hash"] = canonical_hash(record)
        self.records.append(record)
        self.head = record["chain_hash"]
        return record


__all__ = ["ReceiptChain"]
