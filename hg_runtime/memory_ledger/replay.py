"""Phase 26 replay facade."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.memory_ledger.ledger import PersistentMemoryLedger, ReplayResult
from hg_runtime.memory_ledger.schemas import OperationControl


def replay_memory_ledger(path: Path, *, control: OperationControl | None = None) -> ReplayResult:
    return PersistentMemoryLedger(path).replay(control=control)


__all__ = ["replay_memory_ledger"]
