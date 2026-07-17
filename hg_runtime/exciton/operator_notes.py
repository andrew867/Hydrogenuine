"""EXCITON Phase 0 operator notes — drafts, never instructions or consent.

A note/draft is operator-authored text shown back in the OperatorNotesPanel. It carries
``is_instruction=False`` and ``is_consent=False`` and never grants permission or authority.
Notes persist to a local, untracked JSONL store.
"""

from __future__ import annotations

import json
from pathlib import Path

from hg_runtime.exciton.schema import ExcitonOperatorNote, new_id

WORKSPACE = Path(__file__).resolve().parents[2]
DEFAULT_NOTES_PATH = WORKSPACE / ".hg-local" / "exciton" / "operator_notes.jsonl"


def make_note(text: str, created_at: str, kind: str = "draft") -> ExcitonOperatorNote:
    return ExcitonOperatorNote(note_id=new_id("note"), text=text, created_at=created_at, kind=kind)


def append_note(note: ExcitonOperatorNote, path: Path = DEFAULT_NOTES_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(note.to_payload(), sort_keys=True) + "\n")


def load_notes(path: Path = DEFAULT_NOTES_PATH) -> list[ExcitonOperatorNote]:
    if not path.exists():
        return []
    notes: list[ExcitonOperatorNote] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        notes.append(
            ExcitonOperatorNote(
                note_id=d["note_id"], text=d["text"], created_at=d["created_at"], kind=d.get("kind", "draft")
            )
        )
    return notes


__all__ = ["DEFAULT_NOTES_PATH", "append_note", "load_notes", "make_note"]
