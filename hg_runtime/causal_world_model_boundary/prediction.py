"""Prediction records.

A prediction is not verification. Predictions are recorded as UNTESTED (or
synthetic-fixture-only) and authorize no external test.
"""

from __future__ import annotations

from hg_runtime.causal_world_model_boundary.schemas import (
    PREDICTION_RECORD_SCHEMA,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def build_prediction_record(*, hypothesis: dict, status: str = "UNTESTED") -> dict:
    text = f"[prediction implied by {hypothesis['hypothesis_id']}]"
    record = {
        "schema": PREDICTION_RECORD_SCHEMA,
        "prediction_id": f"pred-{hypothesis['hypothesis_id']}",
        "hypothesis_id": hypothesis["hypothesis_id"],
        "prediction_text_hash": canonical_hash({"text": text}),
        "prediction_text_redacted": text,
        "prediction_status": status,
        "prediction_is_verification": False,
        "external_test_authorized": False,
        "tools_authorized": False,
        **neutral_flags(),
    }
    record["record_hash"] = canonical_hash(record)
    return record
