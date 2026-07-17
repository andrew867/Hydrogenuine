"""P26 ledger replay helpers."""

from __future__ import annotations

from hg_runtime.experience_ledger.append_only_ledger import build_ledger_hash_chain, chain_root


def replay_ledger(memory_records: list[dict], expected_root: str | None = None) -> dict:
    chain = build_ledger_hash_chain(memory_records)
    root = chain_root(chain)
    return {
        "record_type": "experience_ledger_replay_result_v1",
        "schema_version": "1",
        "replay_preserves_ledger_hash_chain": expected_root is None or root == expected_root,
        "ledger_chain_root": root,
        "memory_count": len(memory_records),
        "memory_treated_as_truth": False,
        "recall_treated_as_authority": False,
        "belief_promotion_automatic": False,
    }

