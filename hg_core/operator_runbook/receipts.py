"""Emergency receipt recording for break-glass actions (CT-15 RUN)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_core.time.clock import get_clock


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def emergency_receipts_path(workspace: Path, *, relative: str) -> Path:
    return workspace / relative


def record_emergency_receipt(
    workspace: Path,
    *,
    procedure_id: str,
    operator_id: str,
    scope: str,
    payload: dict[str, Any],
    receipts_relative: str = "runtime/ops/emergency_receipts.jsonl",
    ledger_reachable: bool = True,
) -> dict[str, Any]:
    """Always write a local emergency receipt; never skip evidence recording."""
    receipt_id = f"emr-{uuid.uuid4().hex[:12]}"
    receipt = {
        "schema": "emergency_receipt_v1",
        "receipt_id": receipt_id,
        "procedure_id": procedure_id,
        "operator_id": operator_id,
        "scope": scope,
        "recorded_at": _utc_now(),
        "clock_source": type(get_clock()).__name__,
        "ledger_reachable": ledger_reachable,
        "reconciliation_status": "posted" if ledger_reachable else "pending_reconciliation",
        "payload": payload,
    }
    path = emergency_receipts_path(workspace, relative=receipts_relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(receipt, sort_keys=True) + "\n")
    return receipt


def load_receipts(workspace: Path, *, receipts_relative: str) -> list[dict[str, Any]]:
    path = emergency_receipts_path(workspace, relative=receipts_relative)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


__all__ = ["load_receipts", "record_emergency_receipt"]
