"""Checkpoint list and approve/deny for HITL; reads/writes run_dir."""

import json
import time
from pathlib import Path
from .run_index_db import get_run


def _run_dir(run_id: str) -> Path:
    r = get_run(run_id)
    if not r:
        raise FileNotFoundError(run_id)
    return Path(r["run_dir"])


def list_checkpoints(run_id: str) -> list[dict]:
    """Return list of checkpoints for run; empty if run_dir or checkpoints.json missing."""
    try:
        rd = _run_dir(run_id)
    except FileNotFoundError:
        return []
    path = rd / "checkpoints.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("checkpoints", data) if isinstance(data, dict) else data
        if not isinstance(items, list):
            return []
    except (json.JSONDecodeError, OSError):
        return []
    # Merge decisions from checkpoint_decisions/
    decisions_dir = rd / "checkpoint_decisions"
    if decisions_dir.exists():
        for f in decisions_dir.iterdir():
            if f.suffix == ".json" and f.stem:
                try:
                    dec = json.loads(f.read_text(encoding="utf-8"))
                    decision = dec.get("decision", "approved")
                    decided_at = dec.get("decided_at", "")
                    comment = dec.get("comment", "")
                    for cp in items:
                        if cp.get("checkpoint_id") == f.stem:
                            cp["status"] = "approved" if decision == "approved" else "denied"
                            cp["decided_at"] = decided_at
                            cp["comment"] = comment
                            break
                except (json.JSONDecodeError, OSError):
                    pass
    return items


def approve(run_id: str, checkpoint_id: str, comment: str | None = None) -> dict:
    """Persist approval for checkpoint; returns { ok: True } or raises."""
    rd = _run_dir(run_id)
    decisions_dir = rd / "checkpoint_decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    # Safe filename: no path traversal
    if "/" in checkpoint_id or "\\" in checkpoint_id or ".." in checkpoint_id:
        raise ValueError("invalid checkpoint_id")
    path = decisions_dir / f"{checkpoint_id}.json"
    payload = {"decision": "approved", "decided_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "comment": comment or ""}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {"ok": True}


def deny(run_id: str, checkpoint_id: str, comment: str | None = None) -> dict:
    """Persist denial for checkpoint; returns { ok: True } or raises."""
    rd = _run_dir(run_id)
    decisions_dir = rd / "checkpoint_decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    if "/" in checkpoint_id or "\\" in checkpoint_id or ".." in checkpoint_id:
        raise ValueError("invalid checkpoint_id")
    path = decisions_dir / f"{checkpoint_id}.json"
    payload = {"decision": "denied", "decided_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "comment": comment or ""}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {"ok": True}
