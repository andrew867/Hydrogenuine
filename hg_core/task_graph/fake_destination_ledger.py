"""
Fake destination ledger for E2E tests (Phase 6).

Records "would post" events to a local JSONL ledger; no real outbound call.
Assert: one event per logical post; retry sends zero additional events (dedupe).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

FAKE_LEDGER_FILENAME = "e2e_fake_ledger.jsonl"


def get_ledger_path(workspace_root: Path) -> Path:
    """Path to fake destination ledger (JSONL)."""
    return workspace_root / "memory" / "automation" / FAKE_LEDGER_FILENAME


def record_would_post(
    workspace_root: Path,
    run_id: str,
    workflow_id: str,
    content_hash: str,
    destination: str,
    time_bucket: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Append a "would post" event to the fake ledger (no real call)."""
    path = get_ledger_path(workspace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "event": "would_post",
        "run_id": run_id,
        "workflow_id": workflow_id,
        "content_hash": content_hash,
        "destination": destination,
        "time_bucket": time_bucket,
        "ts": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_ledger(workspace_root: Path) -> List[Dict[str, Any]]:
    """Read all entries from the fake ledger (for assertions)."""
    path = get_ledger_path(workspace_root)
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def clear_ledger(workspace_root: Path) -> None:
    """Clear the fake ledger (e.g. between tests)."""
    path = get_ledger_path(workspace_root)
    if path.exists():
        path.unlink()
