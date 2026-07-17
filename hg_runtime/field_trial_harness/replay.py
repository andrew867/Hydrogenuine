"""Deterministic replay for Phase 35 field-trial decisions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.field_trial_harness.schemas import FIELD_TRIAL_REPLAY_RECORD_SCHEMA


class FieldTrialLog:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    def append(self, schema: str, payload: Mapping[str, Any]) -> None:
        row = {"schema": schema, **dict(payload)}
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, sort_keys=True) + "\n")

    def read_all(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows


def replay_decisions(decisions: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    ordered = sorted(decisions, key=lambda row: str(row.get("candidate_id")))
    digest = canonical_hash({"decisions": ordered})
    record = {
        "schema": FIELD_TRIAL_REPLAY_RECORD_SCHEMA,
        "decision_count": len(ordered),
        "replay_digest": digest,
        "deterministic": True,
    }
    record["record_hash"] = canonical_hash(record)
    return record


def replay_from_file(path: Path) -> dict[str, Any]:
    rows = FieldTrialLog(path).read_all()
    decisions = [row for row in rows if row.get("schema", "").endswith("decision_v1") or row.get("final_decision")]
    return replay_decisions(decisions)


__all__ = ["FieldTrialLog", "replay_decisions", "replay_from_file"]
