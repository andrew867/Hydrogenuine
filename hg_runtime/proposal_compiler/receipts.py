"""Phase 37 compiler receipts and deterministic package hashing."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.proposal_compiler.schemas import (
    COMPILER_RECEIPT_SCHEMA,
    assert_neutral_output,
    neutral_flags,
)


def docs_hash(docs: Mapping[str, str]) -> str:
    """Deterministic hash over the document set (order-independent by filename)."""
    return canonical_hash({name: docs[name] for name in sorted(docs)})


def compiler_receipt(
    *,
    proposal_id: str,
    status: str,
    reason: str,
    proposal_hash: str,
    docs: Mapping[str, str],
    classification: Mapping[str, Any],
) -> dict[str, Any]:
    receipt = {
        "schema": COMPILER_RECEIPT_SCHEMA,
        "proposal_id": proposal_id,
        "status": status,
        "reason": reason,
        "proposal_hash": proposal_hash,
        "doc_names": sorted(docs),
        "package_hash": docs_hash(docs),
        "authority_bypass_hits": list(classification.get("authority_bypass_hits", [])),
        "implemented_claim_hits": list(classification.get("implemented_claim_hits", [])),
        "live_action_hits": list(classification.get("live_action_hits", [])),
        "missing_fields": list(classification.get("missing_fields", [])),
        **neutral_flags(),
    }
    assert_neutral_output(receipt)
    receipt["receipt_hash"] = canonical_hash(receipt)
    return receipt


__all__ = ["compiler_receipt", "docs_hash"]
