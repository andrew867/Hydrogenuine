"""
Replay seed_events.jsonl into the workspace ledger (append each envelope to its scope chain).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from hg_core.ledger.ledger_writer import append_event


def replay_seed_into_ledger(
    seed_events_path: Path,
    workspace_root: Path,
    *,
    verify_before_append: bool = True,
) -> List[str]:
    """
    Read seed_events.jsonl and append each event to the ledger (per-scope chain).
    Returns list of event_ids appended.
    """
    workspace_root = Path(workspace_root)
    path = Path(seed_events_path)
    if not path.exists():
        raise FileNotFoundError(f"Seed events file not found: {path}")
    appended: List[str] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ev: Dict[str, Any] = json.loads(line)
            eid = append_event(ev, workspace_root, verify_before_append=verify_before_append)
            appended.append(eid)
    return appended
