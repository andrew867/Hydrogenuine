"""Append-only P26 ledger chain helpers."""

from __future__ import annotations

from hg_runtime.memory_ledger.hash_chain import canonical_hash

from hg_runtime.experience_ledger.hashing import stable_hash


def build_ledger_hash_chain(memory_records: list[dict]) -> list[dict]:
    chain: list[dict] = []
    previous_hash = "GENESIS"
    for index, record in enumerate(memory_records):
        memory_hash = stable_hash(record)
        entry = {
            "record_type": "experience_ledger_hash_chain_entry_v1",
            "schema_version": "1",
            "index": index,
            "memory_id": record["memory_id"],
            "memory_hash": memory_hash,
            "previous_hash": previous_hash,
        }
        entry["chain_hash"] = canonical_hash({k: v for k, v in entry.items() if k != "chain_hash"})
        previous_hash = entry["chain_hash"]
        chain.append(entry)
    return chain


def chain_root(chain: list[dict]) -> str:
    return stable_hash({"chain_hashes": [entry["chain_hash"] for entry in chain]})
