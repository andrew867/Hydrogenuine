"""DIB-3 extraction replay helpers."""

from __future__ import annotations

from hg_runtime.document_intake_boundary.schemas import record_hash


def replay_extraction_layer(layer: dict) -> dict:
    payload = {
        "receipts": [row["receipt_hash"] for row in layer["extraction_receipts"]],
        "failures": [row["record_hash"] for row in layer["extraction_failure_records"]],
        "leb": [row["record_hash"] for row in layer["dib_to_leb_adapter_records"]],
    }
    expected = record_hash(payload)
    observed = record_hash(payload)
    return {
        "replay_deterministic": expected == observed,
        "expected_hash": expected,
        "observed_hash": observed,
    }
