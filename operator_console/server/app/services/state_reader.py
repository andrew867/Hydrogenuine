"""Read run_dir/state.json for node table and run state."""

import json
from pathlib import Path
from .run_index_db import get_run


def _run_dir(run_id: str) -> Path:
    r = get_run(run_id)
    if not r:
        raise FileNotFoundError(run_id)
    return Path(r["run_dir"])


def read_state(run_id: str) -> dict:
    """Return { ok: True, state: ... } or { ok: False, error: { code, message } }."""
    try:
        rd = _run_dir(run_id)
    except FileNotFoundError:
        return {"ok": False, "error": {"code": "NOT_FOUND", "message": "run not found"}}
    path = rd / "state.json"
    if not path.exists():
        return {"ok": False, "error": {"code": "MISSING", "message": "state.json not found"}}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        return {"ok": True, "state": state}
    except (json.JSONDecodeError, OSError) as e:
        return {"ok": False, "error": {"code": "INVALID", "message": str(e)}}
