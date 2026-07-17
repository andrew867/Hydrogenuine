"""EXCITON Phase 0 receipts — evidence of snapshots and control routing.

Receipts are evidence, not authority. Every receipt carries the frozen advisory booleans.
Control receipts append to a local, untracked JSONL so a control request is never executed
without a trace; a missing required receipt is ``RED_EXCITON_MISSING_RECEIPT``.
"""

from __future__ import annotations

import json
from pathlib import Path

from hg_runtime.exciton.schema import (
    ExcitonControlDecision,
    ExcitonReceipt,
    ExcitonStatusSnapshot,
    new_id,
)

WORKSPACE = Path(__file__).resolve().parents[2]
DEFAULT_RECEIPTS_PATH = WORKSPACE / ".hg-local" / "exciton" / "control_receipts.jsonl"


def snapshot_receipt(snapshot: ExcitonStatusSnapshot) -> ExcitonReceipt:
    payload = snapshot.to_payload()
    return ExcitonReceipt(
        receipt_id=new_id("rcpt"),
        kind="snapshot",
        created_at=snapshot.generated_at,
        ref_hash=payload["snapshot_hash"],
        detail={"snapshot_id": snapshot.snapshot_id, "overall_verdict": snapshot.overall_verdict},
    )


def control_receipt(decision: ExcitonControlDecision, created_at: str) -> ExcitonReceipt:
    return ExcitonReceipt(
        receipt_id=new_id("rcpt"),
        kind="control",
        created_at=created_at,
        ref_hash=None,
        detail={
            "request_id": decision.request_id,
            "control": decision.control.value,
            "decision": decision.decision.value,
        },
    )


def append_receipt(receipt: ExcitonReceipt, path: Path = DEFAULT_RECEIPTS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(receipt.to_payload(), sort_keys=True) + "\n")


__all__ = [
    "DEFAULT_RECEIPTS_PATH",
    "append_receipt",
    "control_receipt",
    "snapshot_receipt",
]
