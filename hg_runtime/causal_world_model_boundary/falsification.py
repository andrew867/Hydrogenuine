"""Falsification conditions.

A falsification condition records what would weaken or refute a hypothesis. It is
RECORDED_NOT_EXECUTED and confers no execution authority.
"""

from __future__ import annotations

from hg_runtime.causal_world_model_boundary.schemas import (
    FALSIFICATION_CONDITION_SCHEMA,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def build_falsification_condition(*, hypothesis: dict) -> dict:
    text = f"[falsification condition for {hypothesis['hypothesis_id']} — recorded, not executed]"
    record = {
        "schema": FALSIFICATION_CONDITION_SCHEMA,
        "condition_id": f"falsify-{hypothesis['hypothesis_id']}",
        "hypothesis_id": hypothesis["hypothesis_id"],
        "condition_text_hash": canonical_hash({"text": text}),
        "condition_text_redacted": text,
        "condition_status": "RECORDED_NOT_EXECUTED",
        "execution_authorized": False,
        "tools_authorized": False,
        "falsification_condition_treated_as_execution_authority": False,
        **neutral_flags(),
    }
    record["record_hash"] = canonical_hash(record)
    return record
