"""
Run state persistence for resume and audit.

Saves graph metadata, node states, attempts, outputs, errors, timestamps per run.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .schema import DAG, Node


@dataclass
class RunState:
    """Persisted state for one DAG run."""
    run_id: str
    graph_id: str
    started_at: str
    updated_at: str
    node_outputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    node_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    final_status: Optional[str] = None  # completed | failed | partial
    # Graph-level mutable state (eval writes, loop accumulation under state["loops"][loop_id])
    state: Dict[str, Any] = field(default_factory=dict)
    # Per-loop runtime: loop_id -> { iteration, active, last_condition_value, iteration_started_at, active_iteration }
    loop_state: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # Runtime-only: body_to_loop map for replay adapter (not persisted)
    body_to_loop: Optional[Dict[str, str]] = field(default=None, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "graph_id": self.graph_id,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "node_outputs": dict(self.node_outputs),
            "node_states": dict(self.node_states),
            "final_status": self.final_status,
            "state": dict(self.state),
            "loop_state": dict(self.loop_state),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> RunState:
        return cls(
            run_id=d["run_id"],
            graph_id=d["graph_id"],
            started_at=d["started_at"],
            updated_at=d["updated_at"],
            node_outputs=dict(d.get("node_outputs", {})),
            node_states=dict(d.get("node_states", {})),
            final_status=d.get("final_status"),
            state=dict(d.get("state", {})),
            loop_state=dict(d.get("loop_state", {})),
        )


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _default_base_dir() -> Path:
    """Resolve default DAG runs directory under workspace root. Fallback to cwd-relative if not in workspace."""
    try:
        from hg_lib.config import get_workspace_root
        return get_workspace_root() / "memory" / "automation" / "dag_runs"
    except Exception:
        return Path("memory/automation/dag_runs")


class StateStore:
    """Persist and load run state as JSON files."""

    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            base_dir = _default_base_dir()
        self.base_dir = Path(base_dir)

    def _path(self, run_id: str) -> Path:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        return self.base_dir / f"{run_id}.json"

    def save(self, state: RunState, nodes: List[Node]) -> None:
        """Persist run state and current node states."""
        state.updated_at = _iso_now()
        state.node_states = {n.id: n.to_dict() for n in nodes}
        path = self._path(state.run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state.to_dict(), f, indent=2)

    def load(self, run_id: str) -> Optional[RunState]:
        """Load run state by run_id. Returns None if not found."""
        path = self._path(run_id)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return RunState.from_dict(json.load(f))
