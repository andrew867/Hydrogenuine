"""Read named JSON artifacts from run_dir (e.g. memory.json, context.json)."""

import json
import re
from pathlib import Path
from .run_index_db import get_run


def _run_dir(run_id: str) -> Path:
    r = get_run(run_id)
    if not r:
        raise FileNotFoundError(run_id)
    return Path(r["run_dir"])


# Safe name: alphanumeric, underscore, hyphen only; no path traversal
_SAFE_NAME = re.compile(r"^[a-zA-Z0-9_.-]+$")


def read_json_artifact(run_id: str, name: str) -> dict:
    """Return { ok: True, data: ... } or { ok: False, error: { code, message } }. Name maps to run_dir/{name}.json."""
    if not name or not _SAFE_NAME.match(name):
        return {"ok": False, "error": {"code": "INVALID", "message": "invalid artifact name"}}
    try:
        rd = _run_dir(run_id)
    except FileNotFoundError:
        return {"ok": False, "error": {"code": "NOT_FOUND", "message": "run not found"}}
    path = rd / f"{name}.json"
    if not path.exists():
        return {"ok": False, "error": {"code": "MISSING", "message": f"{name}.json not found"}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {"ok": True, "data": data}
    except (json.JSONDecodeError, OSError) as e:
        return {"ok": False, "error": {"code": "INVALID", "message": str(e)}}
