"""Resolve latest check-in artifact from proof directory.

Check-ins are observation/reporting artifacts only. They are not permits,
approvals, claims, truth, authority, publication, or external effects.
"""

from __future__ import annotations

import re
from pathlib import Path


def resolve_latest_checkin(proof_path: str | Path) -> str:
    """Find the latest hourly_checkins/hour_NN.md in the proof directory."""
    checkins_dir = Path(proof_path) / "hourly_checkins"
    if not checkins_dir.is_dir():
        return ""
    pattern = re.compile(r"^hour_(\d+)\.md$")
    best_hour = -1
    best_path = ""
    for f in checkins_dir.iterdir():
        m = pattern.match(f.name)
        if m:
            hour = int(m.group(1))
            if hour > best_hour:
                best_hour = hour
                best_path = str(f)
    return best_path


def resolve_checkin_from_heartbeat_or_proof(heartbeat: dict | None,
                                            proof_path: str = "") -> str:
    """Return best available checkin path: heartbeat field first, then proof scan."""
    if heartbeat:
        hb_path = heartbeat.get("last_checkin_path", "")
        if hb_path and Path(hb_path).exists():
            return hb_path
        if not proof_path:
            proof_path = heartbeat.get("proof_path", "")
    if proof_path:
        return resolve_latest_checkin(proof_path)
    return ""


def list_checkins(proof_path: str | Path) -> list[str]:
    """List all hourly checkin paths sorted by hour."""
    checkins_dir = Path(proof_path) / "hourly_checkins"
    if not checkins_dir.is_dir():
        return []
    pattern = re.compile(r"^hour_(\d+)\.md$")
    results = []
    for f in sorted(checkins_dir.iterdir()):
        if pattern.match(f.name):
            results.append(str(f))
    return results


def checkin_completeness(proof_path: str | Path) -> dict:
    """Assess checkin artifact completeness. Returns a diagnostic dict."""
    checkins = list_checkins(proof_path)
    checkins_dir = Path(proof_path) / "hourly_checkins"
    jsonl_path = checkins_dir / "hourly_checkins.jsonl" if checkins_dir.is_dir() else None
    has_jsonl = jsonl_path.exists() if jsonl_path else False

    if not checkins and not has_jsonl:
        return {
            "status": "YELLOW_NO_CHECKIN_ARTIFACTS",
            "checkin_count": 0,
            "has_jsonl": False,
            "latest_checkin_path": "",
        }

    return {
        "status": "GREEN_CHECKINS_PRESENT",
        "checkin_count": len(checkins),
        "has_jsonl": has_jsonl,
        "latest_checkin_path": checkins[-1] if checkins else "",
    }
