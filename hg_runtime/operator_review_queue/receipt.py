"""Receipt-chain helpers for Phase 41."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.memory_ledger.hash_chain import canonical_hash


class ReviewReceiptLog:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._head = "sha256:phase41_genesis"
        self._records: list[dict] = []

    def append(self, schema: str, payload: dict) -> dict:
        row = {
            "schema": schema,
            "previous_hash": self._head,
            "payload_hash": canonical_hash(payload),
            "payload": payload,
        }
        row["chain_hash"] = canonical_hash(row)
        self._head = row["chain_hash"]
        self._records.append(row)
        with self.path.open("a", encoding="utf-8") as fh:
            import json

            fh.write(json.dumps(row, sort_keys=True) + "\n")
        return row

    def records(self) -> list[dict]:
        return list(self._records)

    @property
    def head(self) -> str:
        return self._head
