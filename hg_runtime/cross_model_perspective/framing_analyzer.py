"""Record framing signatures descriptively only."""

from __future__ import annotations

from hg_runtime.cross_model_perspective.schemas import FRAMING_SIGNATURE_SCHEMA, neutral_flags
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def analyze_framing(receipts: list[dict]) -> list[dict]:
    signatures: list[dict] = []
    for r in sorted(receipts, key=lambda x: (x["prompt_id"], x["participant_id"])):
        if not r["framing_tags"]:
            continue
        sig = {
            "schema": FRAMING_SIGNATURE_SCHEMA,
            "prompt_id": r["prompt_id"],
            "participant_id": r["participant_id"],
            "receipt_id": r["receipt_id"],
            "framing_tags": r["framing_tags"],
            "descriptive_only": True,
            "framing_is_truth": False,
            "framing_is_authority": False,
            **neutral_flags(),
        }
        sig["signature_hash"] = canonical_hash(sig)
        signatures.append(sig)
    return signatures
