"""Control API receipts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
RECEIPTS_PATH = WORKSPACE / ".hg-local" / "exciton" / "control_receipts.jsonl"


def write_control_receipt(
    *,
    control_id: str,
    decision: str,
    ok: bool,
    human_message: str,
    detail: dict | None = None,
) -> str:
    RECEIPTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    receipt_id = f"crec-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    payload = {
        "receipt_id": receipt_id,
        "control_id": control_id,
        "decision": decision,
        "ok": ok,
        "human_message": human_message[:500],
        "detail": detail or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }
    with RECEIPTS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, sort_keys=True) + "\n")
    return receipt_id


__all__ = ["write_control_receipt"]
