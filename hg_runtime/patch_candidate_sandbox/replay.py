"""Phase 38 patch-sandbox receipt-chain replay.

Mirrors the Phase 37 CompilerLog hash-chain so every patch-candidate evaluation
is auditable and deterministically replayable. Appending a record never applies
a patch, grants authority, or creates a live effect; it only records evidence.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash

GENESIS_HASH = "sha256:phase38_genesis"


class PatchSandboxLog:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.head = None
        for row in self.iter_records():
            self.head = row["chain_hash"]

    def append(self, schema: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        previous = self.head or GENESIS_HASH
        record = {
            "schema": schema,
            "payload": dict(payload),
            "payload_hash": canonical_hash(dict(payload)),
            "previous_hash": previous,
        }
        record["record_id"] = "p38-" + canonical_hash(record).removeprefix("sha256:")[:20]
        record["chain_hash"] = canonical_hash(record)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
        self.head = record["chain_hash"]
        return record

    def iter_records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def replay(self) -> dict[str, Any]:
        previous = GENESIS_HASH
        errors: list[str] = []
        head = None
        count = 0
        for record in self.iter_records():
            if record["previous_hash"] != previous:
                errors.append(f"chain_break:{record['record_id']}")
            if canonical_hash(record["payload"]) != record["payload_hash"]:
                errors.append(f"payload_hash_mismatch:{record['record_id']}")
            chain = dict(record)
            expected = chain.pop("chain_hash")
            if canonical_hash(chain) != expected:
                errors.append(f"chain_hash_mismatch:{record['record_id']}")
            previous = record["chain_hash"]
            head = previous
            count += 1
        return {"ok": not errors, "records": count, "chain_root": head, "errors": errors}


__all__ = ["PatchSandboxLog", "GENESIS_HASH"]
