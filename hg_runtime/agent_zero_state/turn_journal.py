"""TurnJournal — append-only receipt log with hash chain.

Chain enforcement hardened 2026-07-03 (morning hardening tranche): `verify_chain`
now recomputes every entry hash (tampered payloads with stale hash fields fail),
checks the genesis rule (entry 0 must carry null previous_turn_hash), enforces
turn_index monotonicity and run identity constancy, and fails on missing hash
fields. `verify_chain_report()` returns the structured result for gates.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_runtime.agent_zero_state.hashing import hash_record
from hg_runtime.agent_zero_state.turn_receipt import TurnReceipt, validate_turn_receipt


class TurnJournalError(Exception):
    """Journal integrity failure."""


@dataclass
class TurnJournal:
    path: Path

    def ensure_parent(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, receipt: TurnReceipt) -> None:
        """Append one receipt — no mutation of prior lines."""
        verdict, validated = validate_turn_receipt(receipt)
        if verdict.value.startswith("RED_"):
            raise TurnJournalError(f"cannot append invalid receipt: {verdict.value}")
        self.ensure_parent()
        line = json.dumps(validated.to_payload(), sort_keys=True, separators=(",", ":"))
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        entries: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entries.append(json.loads(line))
        return entries

    def read_receipts(self) -> list[TurnReceipt]:
        from hg_runtime.agent_zero_state.replay import receipt_from_journal_entry

        return [receipt_from_journal_entry(entry) for entry in self.read_all()]

    def verify_chain(self) -> None:
        """Verify the hash chain across journal entries. Raises on the first failure.

        Fail-closed checks: recomputed entry hashes (tamper), genesis null link,
        previous_turn_hash linkage, turn_index monotonicity, run/agent constancy,
        missing hash fields.
        """
        report = self.verify_chain_report()
        if report["failures"]:
            f = report["failures"][0]
            raise TurnJournalError(
                f"hash chain break at entry {f['index']}: {f['code']}: {f['detail']}")

    def verify_chain_report(self) -> dict[str, Any]:
        """Structured chain verification for gates: never raises, reports all failures."""
        entries = self.read_all()
        failures: list[dict[str, Any]] = []

        def fail(i: int, code: str, detail: str) -> None:
            failures.append({"index": i, "code": code, "detail": detail})

        prev_hash: str | None = None
        prev_index: int | None = None
        identity: tuple[Any, Any] | None = None
        for i, entry in enumerate(entries):
            declared = entry.get("hash")
            if not declared:
                fail(i, "MISSING_HASH", "entry has no hash field")
            else:
                body = {k: v for k, v in entry.items() if k != "hash"}
                if hash_record(body) != declared:
                    fail(i, "TAMPERED_ENTRY",
                         "recomputed hash does not match stored hash field")
            link = entry.get("previous_turn_hash")
            if i == 0:
                if link is not None:
                    fail(i, "MISSING_GENESIS_NULL",
                         "first journal entry must carry null previous_turn_hash")
            else:
                if link is None:
                    fail(i, "MISSING_PREVIOUS_HASH",
                         "non-genesis entry missing previous_turn_hash")
                elif link != prev_hash:
                    fail(i, "WRONG_PREVIOUS_HASH",
                         f"expected {prev_hash}, got {link}")
            idx = entry.get("turn_index")
            if prev_index is not None and isinstance(idx, int) and idx != prev_index + 1:
                fail(i, "OUT_OF_ORDER", f"turn_index {idx} after {prev_index}")
            ident = (entry.get("run_id"), entry.get("agent_id"))
            if identity is None:
                identity = ident
            elif ident != identity:
                fail(i, "IDENTITY_MISMATCH",
                     f"run/agent identity changed mid-journal: {ident} != {identity}")
            prev_hash = declared
            prev_index = idx if isinstance(idx, int) else prev_index
        verdict = ("YELLOW_EMPTY_JOURNAL" if not entries
                   else ("RED_TURN_CHAIN_INVALID" if failures
                         else "GREEN_TURN_CHAIN_VALID"))
        return {"verdict": verdict, "entries": len(entries), "failures": failures}


def journal_path_for_run(run_id: str, *, base: Path | None = None) -> Path:
    root = base or Path(__file__).resolve().parents[2] / ".hg-local" / "agent_zero" / "state"
    return root / run_id / "turn_journal.jsonl"


def state_path_for_run(run_id: str, *, base: Path | None = None) -> Path:
    root = base or Path(__file__).resolve().parents[2] / ".hg-local" / "agent_zero" / "state"
    return root / run_id / "agent_state.json"


__all__ = [
    "TurnJournal",
    "TurnJournalError",
    "journal_path_for_run",
    "state_path_for_run",
]
