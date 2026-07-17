"""Phase 26 receipt checks."""

from __future__ import annotations

from typing import Mapping, Any

from hg_runtime.memory_ledger.schemas import MemoryLedgerError


def require_receipt_or_proof(payload: Mapping[str, Any]) -> None:
    if not payload.get("receipt_refs") and not payload.get("proof_refs"):
        raise MemoryLedgerError("receipt_required:missing_upstream_receipt_or_proof")


__all__ = ["require_receipt_or_proof"]
