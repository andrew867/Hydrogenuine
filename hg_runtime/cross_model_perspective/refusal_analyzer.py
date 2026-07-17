"""Record refusals without treating refusal as authority."""

from __future__ import annotations

from hg_runtime.cross_model_perspective.schemas import REFUSAL_PATTERN_SCHEMA, neutral_flags
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def analyze_refusals(receipts: list[dict]) -> list[dict]:
    patterns: list[dict] = []
    for r in sorted(receipts, key=lambda x: (x["prompt_id"], x["participant_id"])):
        if r["refusal_state"] != "REFUSED":
            continue
        pattern = {
            "schema": REFUSAL_PATTERN_SCHEMA,
            "prompt_id": r["prompt_id"],
            "participant_id": r["participant_id"],
            "receipt_id": r["receipt_id"],
            "refusal_state": r["refusal_state"],
            "refusal_is_authority": False,
            "refusal_is_truth": False,
            "refusal_is_evidence": False,
            **neutral_flags(),
        }
        pattern["pattern_hash"] = canonical_hash(pattern)
        patterns.append(pattern)
    return patterns
