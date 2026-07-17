"""Append-only conversation receipts."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_runtime.agent_zero_console.redaction import redact_payload, redact_text, sha256
from hg_runtime.agent_zero_console.schema import ConversationReceipt, stable_hash, validate_invariants

WORKSPACE = Path(__file__).resolve().parents[2]
RECEIPTS_PATH = WORKSPACE / ".hg-local/agent_zero_console/receipts.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_receipt(
    *,
    event_type: str,
    conversation_id: str,
    payload: dict[str, Any],
    receipts_path: Path | None = None,
) -> ConversationReceipt:
    redacted, _ = redact_payload(payload)
    if isinstance(redacted, dict):
        for key in list(redacted.keys()):
            if key.endswith("_preview") and isinstance(redacted[key], str):
                redacted[key] = redact_text(redacted[key])
    body = {
        "event_type": event_type,
        "conversation_id": conversation_id,
        **(redacted if isinstance(redacted, dict) else {"payload": redacted}),
        "authority_created": False,
        "permission_granted": False,
        "redaction_applied": True,
        "hidden_chain_of_thought_present": False,
    }
    validate_invariants(body)
    receipt = ConversationReceipt(
        receipt_id=f"azcr-{uuid.uuid4().hex[:12]}",
        event_type=event_type,
        conversation_id=conversation_id,
        created_at=_now(),
        payload=body,
    )
    data = receipt.to_dict()
    path = receipts_path or RECEIPTS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(data, sort_keys=True) + "\n")
    return receipt


def read_receipts(*, limit: int = 200, receipts_path: Path | None = None) -> list[dict[str, Any]]:
    path = receipts_path or RECEIPTS_PATH
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    out: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def receipt_hash_stable(payload: dict[str, Any]) -> str:
    return stable_hash(payload)


__all__ = ["RECEIPTS_PATH", "read_receipts", "receipt_hash_stable", "write_receipt"]
