"""Routing and residency receipts.

A successful routing or residency outcome cannot be recorded without receipts, and
a success claimed over an unhealthy provider or failed check is fake green. Receipts
are records of what happened -- never permission.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.model_router.schemas import (
    GREEN_LIKE,
    MODEL_RESIDENCY_RECEIPT_SCHEMA,
    MODEL_ROUTING_RECEIPT_SCHEMA,
    ModelRouterError,
    neutral_flags,
    reject_authority_payload,
)


def build_routing_receipt(
    *,
    request_id: str,
    status: str,
    receipt_refs: list[str],
    health: Mapping[str, Any] | None = None,
    summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if str(status).lower() in GREEN_LIKE:
        if health is not None and not health.get("healthy"):
            raise ModelRouterError("fake_green_rejected:provider_unhealthy")
        if not receipt_refs:
            raise ModelRouterError("missing_receipt_blocks_success")
    receipt = {
        "schema": MODEL_ROUTING_RECEIPT_SCHEMA,
        "request_id": request_id,
        "status": status,
        "receipt_refs": list(receipt_refs),
        "summary": dict(summary or {}),
        "is_permission": False,
        **neutral_flags(),
    }
    receipt["receipt_hash"] = canonical_hash(receipt)
    return receipt


def build_residency_receipt(
    *,
    action: str,
    status: str,
    receipt_refs: list[str],
    instance_id: str | None = None,
) -> dict[str, Any]:
    if str(status).lower() in GREEN_LIKE and not receipt_refs:
        raise ModelRouterError("missing_receipt_blocks_success")
    receipt = {
        "schema": MODEL_RESIDENCY_RECEIPT_SCHEMA,
        "action": action,
        "status": status,
        "instance_id": instance_id,
        "receipt_refs": list(receipt_refs),
        "is_permission": False,
        **neutral_flags(),
    }
    receipt["receipt_hash"] = canonical_hash(receipt)
    return receipt


def assert_not_permission(record: Mapping[str, Any]) -> Mapping[str, Any]:
    """A defensive guard: a routing/residency record may never carry authority."""
    reject_authority_payload(dict(record))
    return record


__all__ = ["assert_not_permission", "build_residency_receipt", "build_routing_receipt"]
