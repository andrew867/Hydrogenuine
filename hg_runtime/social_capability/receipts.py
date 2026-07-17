"""Social capability receipts — no secrets in receipts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_runtime.exciton.gate_helpers import scan_forbidden
from hg_runtime.social_capability.schema import SocialPublishReceipt

WORKSPACE = Path(__file__).resolve().parents[2]
RECEIPTS_DIR = WORKSPACE / ".hg-local" / "social" / "receipts"


def write_publish_receipt(receipt: SocialPublishReceipt, *, detail: dict[str, Any] | None = None) -> Path:
    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = receipt.to_payload()
    if detail:
        payload["detail"] = {k: v for k, v in detail.items() if "token" not in str(k).lower()}
    forbidden = scan_forbidden(payload)
    if forbidden:
        raise RuntimeError(f"RED_SOCIAL_SECRET_LEAK: {forbidden[:5]}")
    path = RECEIPTS_DIR / f"{receipt.receipt_id}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def append_ewj_stub(receipt: SocialPublishReceipt) -> str:
    """Best-effort EWJ event reference for soak/gates."""
    ewj_dir = WORKSPACE / ".hg-local" / "external_witness_journal"
    ewj_dir.mkdir(parents=True, exist_ok=True)
    event_id = f"social-publish-{receipt.receipt_id}"
    latest = ewj_dir / "latest_event.json"
    payload = {
        "event_id": event_id,
        "kind": "SOCIAL_PUBLISH_RECEIPT",
        "receipt_id": receipt.receipt_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }
    latest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return event_id


def append_review_receipt_line(path: Path, payload: dict[str, Any]) -> None:
    forbidden = scan_forbidden(payload)
    if forbidden:
        raise RuntimeError(f"RED_SOCIAL_SECRET_LEAK: {forbidden[:5]}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, sort_keys=True) + "\n")


__all__ = ["append_ewj_stub", "append_review_receipt_line", "write_publish_receipt"]
