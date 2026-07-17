"""Soak receipts and EWJ stubs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from hg_runtime.bounded_soak.schema import SoakReceipt

WORKSPACE = Path(__file__).resolve().parents[2]
RECEIPTS_DIR = WORKSPACE / ".hg-local" / "soak" / "receipts"


def write_soak_receipt(receipt: SoakReceipt) -> Path:
    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RECEIPTS_DIR / f"{receipt.receipt_id}.json"
    path.write_text(json.dumps(receipt.to_payload(), indent=2, sort_keys=True), encoding="utf-8")
    return path


def ewj_soak_event(run_id: str, kind: str) -> str:
    ewj_dir = WORKSPACE / ".hg-local" / "external_witness_journal"
    ewj_dir.mkdir(parents=True, exist_ok=True)
    event_id = f"soak-{kind}-{run_id}"
    payload = {
        "event_id": event_id,
        "kind": f"SOAK_{kind.upper()}",
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }
    (ewj_dir / "latest_event.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return event_id


__all__ = ["ewj_soak_event", "write_soak_receipt"]
