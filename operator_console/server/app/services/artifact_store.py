from pathlib import Path
from ..core.config import settings
from .run_index_db import get_run

def _rd(run_id: str) -> Path:
    r = get_run(run_id)
    if not r:
        raise FileNotFoundError(run_id)
    return Path(r["run_dir"])

def list_artifacts(run_id: str):
    rd = _rd(run_id)
    return sorted([str(p.relative_to(rd)) for p in rd.rglob("*") if p.is_file()])

def resolve_artifact_path(run_id: str, rel_path: str) -> str:
    rd = _rd(run_id)
    # basic traversal protection
    p = (rd / rel_path).resolve()
    if rd.resolve() not in p.parents and rd.resolve() != p:
        raise FileNotFoundError("invalid path")
    if not p.exists():
        raise FileNotFoundError(rel_path)
    return str(p)
