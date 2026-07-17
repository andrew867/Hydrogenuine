"""State history snapshots and run forking."""

from pathlib import Path
import json
import uuid
import time

from .run_index_db import get_run, upsert_run
from ..core.config import settings

# Optional: use hg_core fork helper when workspace on path
try:
    import sys
    _workspace_root = Path(__file__).resolve().parents[4]
    if str(_workspace_root) not in sys.path:
        sys.path.insert(0, str(_workspace_root))
    from hg_core.task_graph.state_history import fork_from_snapshot as _core_fork
except Exception:
    _core_fork = None


def _rd(run_id: str) -> Path:
    r = get_run(run_id)
    if not r:
        raise FileNotFoundError(run_id)
    return Path(r["run_dir"])


def list_snapshots(run_id: str):
    rd = _rd(run_id)
    idx = rd / "state_history" / "index.jsonl"
    if not idx.exists():
        return []
    out = []
    for line in idx.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def load_snapshot(run_id: str, seq: int):
    rd = _rd(run_id)
    p = rd / "state_history" / f"state_{seq:06d}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def fork_from_snapshot(run_id: str, seq: int):
    """Create a new run from a snapshot and register it in the run index."""
    if _core_fork is None:
        return {
            "ok": False,
            "error": {
                "code": "HG_CORE_REQUIRED",
                "message": "Fork requires hg_core installed.",
                "remediation": "Install the workspace package (pip install -e .) and ensure HG_WORKSPACE points to a repo with hg_core. See docs/guides/SETUP_GUIDE_FOR_BEGINNERS.md or docs/runbooks/OPERATOR_REPLAY_FORK.md.",
            },
        }
    r = get_run(run_id)
    if not r:
        return {"ok": False, "error": {"code": "NOT_FOUND", "message": "run not found"}}
    src_run_dir = Path(r["run_dir"])
    if not (src_run_dir / "state_history" / f"state_{seq:06d}.json").exists():
        return {"ok": False, "error": {"code": "NOT_FOUND", "message": f"snapshot {seq} not found"}}
    new_run_id = str(uuid.uuid4())
    root = Path(settings.runs_root)
    root.mkdir(parents=True, exist_ok=True)
    dst_run_dir = root / new_run_id
    dst_run_dir.mkdir(parents=True, exist_ok=True)
    _core_fork(str(src_run_dir), seq, str(dst_run_dir), new_run_id)
    # Copy graph so forked run has a DAG to resume with
    for name in ("graph.reviewed.json", "graph.json"):
        src_graph = src_run_dir / name
        if src_graph.exists():
            (dst_run_dir / "graph.json").write_text(src_graph.read_text(encoding="utf-8"), encoding="utf-8")
            break
    # Persist state so StateStore.load(new_run_id) finds it (executor resume uses runs_root/run_id.json)
    state_path = root / f"{new_run_id}.json"
    state = json.loads((dst_run_dir / "state.json").read_text(encoding="utf-8"))
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    upsert_run({
        "run_id": new_run_id,
        "graph_id": r.get("graph_id"),
        "status": "forked",
        "started_at": time.time(),
        "ended_at": None,
        "run_dir": str(dst_run_dir),
    })
    return {"ok": True, "run_id": new_run_id, "run_dir": str(dst_run_dir), "graph_id": r.get("graph_id")}
