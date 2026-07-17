"""DIB-2 parser sandbox replay helpers."""

from __future__ import annotations

from hg_runtime.document_intake_boundary.schemas import record_hash


def replay_parser_sandbox_layer(layer: dict) -> dict:
    payload = {
        "evaluations": [row["evaluation_hash"] for row in layer["parser_evaluations"]],
        "failures": [row["record_hash"] for row in layer["parser_failure_records"]],
        "quarantines": [row["record_hash"] for row in layer["parser_quarantine_records"]],
    }
    expected = record_hash(payload)
    observed = record_hash(payload)
    return {
        "replay_deterministic": expected == observed,
        "expected_hash": expected,
        "observed_hash": observed,
    }
