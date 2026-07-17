"""TurnJournal tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.agent_zero_state.turn_journal import TurnJournal, TurnJournalError  # noqa: E402
from hg_runtime.agent_zero_state.turn_receipt import build_turn_receipt  # noqa: E402


def _receipt(turn_index: int, previous: str | None = None):
    _, r = build_turn_receipt(
        agent_id="agent-j",
        turn_index=turn_index,
        runtime_mode="local_dev",
        observe_snapshot_ref=f"snap-{turn_index}",
        capability_menu_ref="menu-1",
        chosen_action="rest_turn",
        previous_turn_hash=previous,
        receipt_id=f"rcpt-{turn_index}",
        turn_started_at="2026-06-17T00:00:00+00:00",
        turn_finished_at="2026-06-17T00:00:01+00:00",
    )
    return r


def test_turn_journal_append_and_read(tmp_path: Path):
    journal = TurnJournal(tmp_path / "turn_journal.jsonl")
    r1 = _receipt(1)
    journal.append(r1)
    entries = journal.read_all()
    assert len(entries) == 1
    assert entries[0]["receipt_id"] == "rcpt-1"


def test_turn_journal_hash_chain(tmp_path: Path):
    journal = TurnJournal(tmp_path / "turn_journal.jsonl")
    r1 = _receipt(1)
    r2 = _receipt(2, previous=r1.hash)
    journal.append(r1)
    journal.append(r2)
    journal.verify_chain()


def test_corrupt_journal_fails_chain(tmp_path: Path):
    journal = TurnJournal(tmp_path / "turn_journal.jsonl")
    r1 = _receipt(1)
    r2 = _receipt(2, previous="wrong-hash")
    journal.append(r1)
    journal.append(r2)
    with pytest.raises(TurnJournalError):
        journal.verify_chain()
