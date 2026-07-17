"""Phase 40 append-only repair replay."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash

GENESIS_HASH = "sha256:phase40_genesis"


class RepairLog:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.head = None
        for row in self.records():
            self.head = row["chain_hash"]

    def append(self, schema: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        previous = self.head or GENESIS_HASH
        rec = {"schema": schema, "payload": dict(payload), "payload_hash": canonical_hash(dict(payload)), "previous_hash": previous}
        rec["record_id"] = "p40-" + canonical_hash(rec).removeprefix("sha256:")[:20]
        rec["chain_hash"] = canonical_hash(rec)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(rec, sort_keys=True) + "\n")
        self.head = rec["chain_hash"]
        return rec

    def records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]


def replay_records(records: list[Mapping[str, Any]]) -> dict[str, Any]:
    prev = GENESIS_HASH
    errors: list[str] = []
    head = None
    for rec in records:
        if rec["previous_hash"] != prev:
            errors.append("chain_break")
        if canonical_hash(rec["payload"]) != rec["payload_hash"]:
            errors.append("payload_hash_mismatch")
        copy = dict(rec)
        expected = copy.pop("chain_hash")
        if canonical_hash(copy) != expected:
            errors.append("chain_hash_mismatch")
        if rec["schema"] == "ledger_repair_record_v1" and not rec["payload"].get("original_record_hash"):
            errors.append("missing_original_hash")
        prev = rec["chain_hash"]
        head = prev
    return {"ok": not errors, "records": len(records), "chain_root": head, "errors": errors}

