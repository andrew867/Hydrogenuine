"""WILL profile registry and config loading."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hg_runtime.will_module.envelope import WillEnvelope, build_envelope_from_config
from hg_runtime.will_module.receipts import WillReceipt, create_envelope_receipt
from hg_runtime.will_module.schema import WillSource

WORKSPACE = Path(__file__).resolve().parents[2]
DEFAULT_WILL_DIR = WORKSPACE / "configs" / "will"


def load_will_config(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        p = WORKSPACE / path
    data = json.loads(p.read_text(encoding="utf-8"))
    if data.get("permission_granted") or data.get("authority_created"):
        raise ValueError("will config must not grant permission or authority")
    return data


def load_will_envelope(
    path: str | Path,
    *,
    run_id: str,
    source: WillSource = WillSource.OPERATOR,
) -> tuple[WillEnvelope, WillReceipt]:
    config = load_will_config(path)
    envelope = build_envelope_from_config(config, run_id=run_id, source=source)
    receipt = create_envelope_receipt(envelope.semantic_payload(), event_type="WILL_PROFILE_LOADED")
    envelope.finalize(receipt_ref=receipt.receipt_id)
    return envelope, receipt


__all__ = ["DEFAULT_WILL_DIR", "WORKSPACE", "load_will_config", "load_will_envelope"]
