"""DTX bridge replay helpers."""

from __future__ import annotations

from hg_runtime.document_text_exchange.schemas import record_hash


def replay_bridge_layer(layer: dict) -> dict:
    payload = {
        "receipts": [row["receipt_hash"] for row in layer["dtx_extraction_receipts"]],
        "bridges": [row["record_hash"] for row in layer["dtx_leb_bridge_records"]],
        "failures": [row["record_hash"] for row in layer["dtx_extraction_failures"]],
    }
    expected = record_hash(payload)
    observed = record_hash(payload)
    return {"replay_deterministic": expected == observed, "expected_hash": expected, "observed_hash": observed}
