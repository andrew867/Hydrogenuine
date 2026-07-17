"""Append-only recognition trace store (G16 / G15 retention)."""
from __future__ import annotations

import json
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _default_traces_root() -> Path:
    try:
        from hg_lib.config import get_workspace_root

        return Path(get_workspace_root()) / "memory" / "governance" / "recognition_traces"
    except Exception:
        return Path("memory/governance/recognition_traces")


class RecognitionTraceStore:
    """Per-subject append-only JSONL recognition traces."""

    root: Path
    _lock: threading.Lock

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = Path(root) if root is not None else _default_traces_root()
        self._lock = threading.Lock()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, subject_id: str) -> Path:
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in subject_id)
        return self.root / f"{safe}.jsonl"

    def append(self, *, subject_id: str, record: Dict[str, Any]) -> Dict[str, Any]:
        row = dict(record)
        row.setdefault("recognition_id", f"rec_{uuid.uuid4().hex[:10]}")
        row.setdefault("subject_id", subject_id)
        row.setdefault("ts", time.time())
        row.setdefault("recorded_at", _iso_now())
        path = self._path_for(subject_id)
        with self._lock:
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row

    def read_all(self, subject_id: Optional[str] = None, *, limit: int = 100) -> List[Dict[str, Any]]:
        paths = [self._path_for(subject_id)] if subject_id else sorted(self.root.glob("*.jsonl"))
        rows: List[Dict[str, Any]] = []
        for path in paths:
            if not path.exists():
                continue
            with path.open(encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return rows[-limit:] if limit > 0 else rows
