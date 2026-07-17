"""Message Center persistence."""

from __future__ import annotations

import json
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
ROOT = WORKSPACE / ".hg-local/message_center"


class MessageCenterStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self.items_path = self.root / "messages.jsonl"

    def append(self, item: dict) -> None:
        with self.items_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(item, sort_keys=True) + "\n")

    def list_items(self) -> list[dict]:
        if not self.items_path.is_file():
            return []
        return [json.loads(line) for line in self.items_path.read_text(encoding="utf-8").splitlines() if line.strip()]


__all__ = ["MessageCenterStore", "ROOT"]
