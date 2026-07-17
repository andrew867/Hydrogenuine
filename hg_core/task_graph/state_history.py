"""State history snapshot helpers for durable DAG runs (time travel, fork from snapshot)."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


def _hist_dir(run_dir: Union[Path, str]) -> Path:
    d = Path(run_dir) / "state_history"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _next_seq(hd: Path) -> int:
    files = sorted(hd.glob("state_*.json"))
    if not files:
        return 1
    try:
        return int(files[-1].stem.split("_")[-1]) + 1
    except Exception:
        return len(files) + 1


def write_snapshot(
    run_dir: Union[Path, str],
    run_state: Dict[str, Any],
    reason: str,
    node_id: Optional[str] = None,
    event_idx: Optional[int] = None,
) -> Dict[str, Any]:
    """Append a state snapshot to state_history/ and index.jsonl. Returns index entry."""
    hd = _hist_dir(run_dir)
    seq = _next_seq(hd)
    name = f"state_{seq:06d}.json"
    (hd / name).write_text(json.dumps(run_state, indent=2), encoding="utf-8")
    entry: Dict[str, Any] = {
        "seq": seq,
        "ts": time.time(),
        "reason": reason,
        "state_path": str(Path("state_history") / name),
    }
    if event_idx is not None:
        entry["event_idx"] = event_idx
    if node_id is not None:
        entry["node_id"] = node_id
    with (hd / "index.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    (hd / "state_latest.json").write_text(json.dumps(run_state, indent=2), encoding="utf-8")
    return entry


def list_snapshots(run_dir: Union[Path, str]) -> List[Dict[str, Any]]:
    """Return list of index entries (one per snapshot) from state_history/index.jsonl."""
    idx = Path(run_dir) / "state_history" / "index.jsonl"
    if not idx.exists():
        return []
    return [
        json.loads(line)
        for line in idx.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_snapshot(run_dir: Union[Path, str], seq: int) -> Dict[str, Any]:
    """Load state dict for the given sequence number."""
    p = Path(run_dir) / "state_history" / f"state_{seq:06d}.json"
    return json.loads(p.read_text(encoding="utf-8"))


def fork_from_snapshot(
    src_run_dir: Union[Path, str],
    seq: int,
    dst_run_dir: Union[Path, str],
    new_run_id: str,
) -> Dict[str, Any]:
    """Copy state at seq from src_run_dir to dst_run_dir/state.json with new_run_id. Returns state dict."""
    st = load_snapshot(src_run_dir, seq)
    st = dict(st)
    st["run_id"] = new_run_id
    dst = Path(dst_run_dir)
    dst.mkdir(parents=True, exist_ok=True)
    (dst / "state.json").write_text(json.dumps(st, indent=2), encoding="utf-8")
    return st
