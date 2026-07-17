"""DURABLE_SQLITE_OR_STORE_SINK — append-only JSONL store in sandbox."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hg_core.dse.config import dse_store_sink_root, ensure_sandbox_dirs
from hg_core.dse.errors import DSE_ROLLBACK_RECORDED, DSE_SINK_COMMITTED, REFUSED_UNAUTHORIZED_PATH
from hg_core.dse.no_authority import advisory_only_marker
from hg_core.dse.policy import SinkClass
from hg_core.dse.sandbox import validate_path_in_sandbox
from hg_core.dse.types import DurableSinkReceipt, SinkRollbackRecord
from hg_core.governance.canonical_hash import canonical_hash
from hg_core.policy_safety.hashing import compute_record_hash


def append_store_record(
    *,
    request_id: str,
    tranche_id: str,
    namespace: str,
    record: dict[str, Any],
    observed_at: str,
    transaction_id: str | None = None,
) -> dict[str, Any]:
    """Append record to governed namespace store; reversible via rollback log."""
    ensure_sandbox_dirs()
    root = dse_store_sink_root()
    store_name = f"{namespace}.jsonl"
    ok, reason, target = validate_path_in_sandbox(store_name, allowed_root=root)
    if not ok or target is None:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": reason or REFUSED_UNAUTHORIZED_PATH,
            "durable_write_performed": False,
        }

    txn_id = transaction_id or f"txn-{compute_record_hash({'request_id': request_id})[-12:]}"
    entry = {
        "transaction_id": txn_id,
        "request_id": request_id,
        "namespace": namespace,
        "record": record,
        "observed_at": observed_at,
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")

    content_digest = canonical_hash(entry)
    receipt_id = f"dse-store-{txn_id}"
    rollback_log = root / f"{namespace}.rollback.jsonl"
    rollback_entry = {"transaction_id": txn_id, "action": "append", "target": str(target), "receipt_id": receipt_id}
    with rollback_log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(rollback_entry, sort_keys=True) + "\n")

    receipt = DurableSinkReceipt(
        receipt_id=receipt_id,
        sink_class=SinkClass.DURABLE_SQLITE_OR_STORE_SINK.value,
        tranche_id=tranche_id,
        request_id=request_id,
        target_ref=str(target.relative_to(root)),
        content_digest=content_digest,
        rollback_marker_ref=str(rollback_log.relative_to(root)),
        observed_at=observed_at,
        extra={"transaction_id": txn_id, "namespace": namespace},
    )
    rollback = SinkRollbackRecord(
        rollback_id=f"dse-rbk-{txn_id}",
        receipt_id=receipt_id,
        tranche_id=tranche_id,
        target_ref=str(target.relative_to(root)),
        rollback_digest=canonical_hash(rollback_entry),
        observed_at=observed_at,
    )

    return {
        **advisory_only_marker(),
        "status": "committed",
        "reason_code": DSE_SINK_COMMITTED,
        "sink_class": SinkClass.DURABLE_SQLITE_OR_STORE_SINK.value,
        "durable_write_performed": True,
        "transaction_id": txn_id,
        "receipt": receipt.to_payload(),
        "rollback": rollback.to_payload(),
        "rollback_reason_code": DSE_ROLLBACK_RECORDED,
        "observed_at": observed_at,
    }


def readback_store(namespace: str, *, limit: int = 100) -> list[dict[str, Any]]:
    root = dse_store_sink_root()
    target = root / f"{namespace}.jsonl"
    if not target.exists():
        return []
    lines = target.read_text(encoding="utf-8").splitlines()
    records: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        if line.strip():
            records.append(json.loads(line))
    return records


__all__ = ["append_store_record", "readback_store"]
