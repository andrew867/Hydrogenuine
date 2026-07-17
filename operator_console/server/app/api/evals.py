"""Pack 19: Evals summary and trends for operator analytics."""

import os
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from ..core.auth import require_api_key

router = APIRouter()


def _evals_latest_dir() -> Path:
    root = os.environ.get("HG_WORKSPACE", ".")
    return Path(root) / "artifacts" / "evals" / "latest"


@router.get("/summary")
def evals_summary(_=Depends(require_api_key)):
    """GET latest eval report (eval_report.json). Returns 404 if no evals run yet."""
    d = _evals_latest_dir()
    path = d / "eval_report.json"
    if not path.exists():
        return {"ok": False, "error": "No eval report found; run scripts/evals/run.py first"}
    import json
    data = json.loads(path.read_text(encoding="utf-8"))
    return {"ok": True, "report": data}


@router.get("/summary/md")
def evals_summary_md(_=Depends(require_api_key)):
    """GET latest eval_summary.md as plain text."""
    path = _evals_latest_dir() / "eval_summary.md"
    if not path.exists():
        return PlainTextResponse("No eval summary found.", status_code=404)
    return PlainTextResponse(path.read_text(encoding="utf-8"))


@router.get("/trends")
def evals_trends(_=Depends(require_api_key)):
    """GET trends.csv rows (timestamp, pass_rate, passed, total)."""
    path = _evals_latest_dir() / "trends.csv"
    if not path.exists():
        return {"ok": True, "rows": []}
    import csv
    text = path.read_text(encoding="utf-8").strip()
    lines = text.split("\n") if text else []
    if not lines:
        return {"ok": True, "rows": []}
    rows = list(csv.DictReader(lines))
    return {"ok": True, "rows": rows}
