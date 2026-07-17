"""
Circuit breaker (F5) per workflow and optionally per destination.

After N consecutive failures, trip the breaker; allow_side_effect returns False
until reset_breaker is called (or cooldown expires in a future extension).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

CIRCUIT_BREAKER_DIR = "memory/automation/circuit_breaker"
DEFAULT_FAILURE_THRESHOLD = 3
DEFAULT_COOLDOWN_SEC = 300  # 5 min; optional for future use


def _breaker_path(workspace_root: Path, workflow_id: str, destination: Optional[str] = None) -> Path:
    base = workspace_root / CIRCUIT_BREAKER_DIR
    if destination:
        return base / f"{workflow_id}" / f"{destination}.json"
    return base / f"{workflow_id}.json"


def _load_state(path: Path) -> dict:
    if not path.exists():
        return {"failures": 0, "tripped_at": None}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"failures": 0, "tripped_at": None}
    except (json.JSONDecodeError, OSError):
        return {"failures": 0, "tripped_at": None}


def _save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def record_failure(
    workspace_root: Path,
    workflow_id: str,
    destination: Optional[str] = None,
    threshold: int = DEFAULT_FAILURE_THRESHOLD,
) -> None:
    """Record a failure for (workflow_id, destination). Trip breaker when failures >= threshold."""
    path = _breaker_path(workspace_root, workflow_id, destination)
    state = _load_state(path)
    state["failures"] = state.get("failures", 0) + 1
    if state["failures"] >= threshold:
        if not state.get("tripped_at"):
            state["tripped_at"] = time.time()
    _save_state(path, state)


def allow_side_effect(
    workspace_root: Path,
    workflow_id: str,
    destination: Optional[str] = None,
) -> bool:
    """Return False if breaker is tripped for (workflow_id, destination); else True."""
    path = _breaker_path(workspace_root, workflow_id, destination)
    state = _load_state(path)
    if not state.get("tripped_at"):
        return True
    # Optional: check cooldown and auto-reset
    cooldown = state.get("cooldown_sec", DEFAULT_COOLDOWN_SEC)
    if cooldown > 0 and (time.time() - state["tripped_at"]) >= cooldown:
        state["tripped_at"] = None
        state["failures"] = 0
        _save_state(path, state)
        return True
    return False


def reset_breaker(
    workspace_root: Path,
    workflow_id: str,
    destination: Optional[str] = None,
) -> None:
    """Clear trip state for (workflow_id, destination)."""
    path = _breaker_path(workspace_root, workflow_id, destination)
    state = _load_state(path)
    state["failures"] = 0
    state["tripped_at"] = None
    _save_state(path, state)


class CircuitBreaker:
    """Convenience wrapper: record_failure / allow_side_effect / reset with same workspace and key."""

    def __init__(self, workspace_root: Path, workflow_id: str, destination: Optional[str] = None):
        self.workspace_root = Path(workspace_root)
        self.workflow_id = workflow_id
        self.destination = destination

    def record_failure(self) -> None:
        record_failure(self.workspace_root, self.workflow_id, self.destination)

    def allow_side_effect(self) -> bool:
        return allow_side_effect(self.workspace_root, self.workflow_id, self.destination)

    def reset(self) -> None:
        reset_breaker(self.workspace_root, self.workflow_id, self.destination)
