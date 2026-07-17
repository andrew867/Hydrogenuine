"""Persistent watchtower store — JSONL events + snapshot file."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from hg_runtime.openvino_watchtower.schema import TelemetrySnapshot, validate_snapshot_dict

WORKSPACE = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = WORKSPACE / ".hg-local" / "openvino_watchtower"
DEFAULT_SNAPSHOT_PATH = DEFAULT_ROOT / "snapshot.json"

_lock = threading.Lock()


class WatchtowerStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or DEFAULT_ROOT
        self.events_path = self.root / "events.jsonl"
        self.snapshot_path = self.root / "snapshot.json"

    def ensure_dirs(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def write_snapshot(self, snapshot: TelemetrySnapshot | dict[str, Any]) -> Path:
        data = snapshot.to_dict() if isinstance(snapshot, TelemetrySnapshot) else dict(snapshot)
        errors = validate_snapshot_dict(data)
        if errors:
            data.setdefault("error_summary", {})["validation_errors"] = errors
        with _lock:
            self.ensure_dirs()
            self.snapshot_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        return self.snapshot_path

    def read_snapshot(self) -> dict[str, Any] | None:
        if not self.snapshot_path.is_file():
            return None
        try:
            return json.loads(self.snapshot_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def append_event_line(self, line: str) -> None:
        with _lock:
            self.ensure_dirs()
            with self.events_path.open("a", encoding="utf-8") as fh:
                fh.write(line.rstrip() + "\n")


__all__ = ["DEFAULT_ROOT", "DEFAULT_SNAPSHOT_PATH", "WatchtowerStore"]
