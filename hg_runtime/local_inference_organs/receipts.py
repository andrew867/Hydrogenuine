"""Receipt helpers for local inference organs."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.local_inference_organs.schemas import (
    ORGAN_AUTHORITY_BOUNDARY_RECEIPT_SCHEMA,
    neutral_flags,
    reject_authority_payload,
)


def receipt_hash(payload: Mapping[str, Any]) -> str:
    return canonical_hash(dict(payload))


def authority_boundary_receipt(*, refs: list[str] | None = None) -> dict[str, Any]:
    receipt = {
        "schema": ORGAN_AUTHORITY_BOUNDARY_RECEIPT_SCHEMA,
        "refs": list(refs or []),
        "organ_outputs_are_advisory": True,
        "model_response_is_not_truth": True,
        "organ_route_is_not_permission": True,
        "loaded_model_is_not_permission": True,
        **neutral_flags(),
    }
    reject_authority_payload(receipt)
    receipt["receipt_hash"] = receipt_hash(receipt)
    return receipt


__all__ = ["authority_boundary_receipt", "receipt_hash"]
