"""Workbench invocation receipts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.workbench.schemas import TOOL_INVOCATION_RECEIPT_SCHEMA, WorkbenchError


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def build_invocation_receipt(
    *,
    request: Mapping[str, Any],
    status: str,
    result: Mapping[str, Any],
    receipt_refs: list[str],
    created_at: str | None = None,
) -> dict[str, Any]:
    if result.get("claims_live_completion") and request.get("mode") == "dry_run":
        raise WorkbenchError("fake_green_rejected:dry_run_result_cannot_claim_live_completion")
    if str(status).lower() in {"success", "green", "passed"} and not receipt_refs:
        raise WorkbenchError("missing_receipt_blocks_success")
    receipt = {
        "schema": TOOL_INVOCATION_RECEIPT_SCHEMA,
        "request_id": request["request_id"],
        "tool_id": request["tool_id"],
        "operation": request["operation"],
        "mode": request["mode"],
        "status": status,
        "result_hash": canonical_hash(dict(result)),
        "receipt_refs": receipt_refs,
        "created_at": created_at or _utc_now(),
        "authority_created": False,
        "permission_granted": False,
        "tool_authorized": False,
        "live_side_effects_created": False,
    }
    receipt["receipt_hash"] = canonical_hash(receipt)
    return receipt


__all__ = ["build_invocation_receipt"]
