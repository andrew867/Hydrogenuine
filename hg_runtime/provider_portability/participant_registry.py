"""Model participant registry."""

from __future__ import annotations

from hg_runtime.memory_ledger.hash_chain import canonical_hash


def registry(participants: list[dict]) -> dict:
    row = {
        "schema": "model_participant_registry_v1",
        "participant_count": len(participants),
        "participant_ids": [p["participant_id"] for p in participants],
        "participant_registration_is_not_trust": all(not p["registration_is_trust"] for p in participants),
    }
    row["registry_hash"] = canonical_hash(row)
    return row
