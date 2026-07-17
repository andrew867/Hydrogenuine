"""Phase 26 redaction facade."""

from __future__ import annotations

from hg_runtime.memory_ledger.ledger import LedgerEntry, PersistentMemoryLedger


def redact_entry(ledger: PersistentMemoryLedger, entry_id: str, *, reason: str) -> LedgerEntry:
    return ledger.redact(entry_id, reason=reason)


__all__ = ["redact_entry"]
