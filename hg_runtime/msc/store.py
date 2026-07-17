"""MSC summary reference store — observation receipts, not authority."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hg_core.ledger.canonical_json import canonical_dumps


def _index_path(runtime_dir: Path) -> Path:
    return Path(runtime_dir) / "msc_index.json"


def load_previous_summary_ref(runtime_dir: Path, agent_id: str) -> str | None:
    path = _index_path(runtime_dir)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    agents = data.get("agents", {})
    if not isinstance(agents, dict):
        return None
    entry = agents.get(agent_id)
    if not isinstance(entry, dict):
        return None
    ref = entry.get("last_summary_ref")
    return str(ref) if ref else None


def store_summary_ref(
    runtime_dir: Path,
    *,
    agent_id: str,
    cycle_id: str,
    summary_id: str,
    summary_hash: str,
) -> str:
    """Persist summary reference; returns memory_ref id."""
    path = _index_path(runtime_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {"agents": {}}
    else:
        data = {"agents": {}}
    agents = data.setdefault("agents", {})
    memory_ref = f"msc:{agent_id}:{summary_id}"
    agents[agent_id] = {
        "last_summary_ref": memory_ref,
        "last_cycle_id": cycle_id,
        "last_summary_hash": summary_hash,
        "observation_only": True,
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(canonical_dumps(data))
    tmp.replace(path)
    return memory_ref


__all__ = ["load_previous_summary_ref", "store_summary_ref"]
