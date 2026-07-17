"""Trust metrics aggregation for proof viewer (delegates to hg_gateway proof metrics)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends

from hg_gateway.admin_proofs import _proof_metrics, _proofs_workspace
from ..core.auth import require_api_key

router = APIRouter()


def _load_proof_index() -> Dict[str, Any]:
    idx_path = _proofs_workspace() / "docs" / "proofs" / "index.json"
    if not idx_path.exists():
        return {"latest": {}, "runs": []}
    try:
        index = json.loads(idx_path.read_text(encoding="utf-8"))
        if not isinstance(index, dict):
            return {"latest": {}, "runs": []}
        return index
    except (json.JSONDecodeError, OSError):
        return {"latest": {}, "runs": []}


@router.get("/trust-metrics")
def get_trust_metrics(_=Depends(require_api_key)) -> Dict[str, Any]:
    """Return proof trust metrics for operator console proof viewer."""
    index = _load_proof_index()
    metrics = _proof_metrics(index)
    return {
        "ok": True,
        "index": {
            "latest": index.get("latest") if isinstance(index.get("latest"), dict) else {},
            "runs": index.get("runs") if isinstance(index.get("runs"), list) else [],
        },
        "metrics": metrics,
        "workspace": str(_proofs_workspace()),
        "hg_workspace_env": os.environ.get("HG_WORKSPACE"),
    }
