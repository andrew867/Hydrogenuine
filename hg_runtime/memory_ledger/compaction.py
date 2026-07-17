"""Phase 26 compaction facade."""

from __future__ import annotations

from hg_runtime.memory_ledger.ledger import CompactionReceipt, PersistentMemoryLedger
from hg_runtime.memory_ledger.schemas import OperationControl


def compact_ledger(
    ledger: PersistentMemoryLedger,
    *,
    summary: str,
    receipt_refs: list[str],
    control: OperationControl | None = None,
) -> CompactionReceipt:
    return ledger.compact(summary=summary, receipt_refs=receipt_refs, control=control)


__all__ = ["compact_ledger"]
