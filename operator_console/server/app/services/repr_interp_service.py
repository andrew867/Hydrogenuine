"""
Layer 8 Phase 4: Representation interpretability for operator console.
Exposes inspection results and proof-path (with representation_inspection_result) via workspace.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

def _workspace_root() -> Path | None:
    try:
        from hg_lib.config import get_workspace_root
        return get_workspace_root()
    except Exception:
        return None


def get_repr_interp_results(
    run_id: str | None = None,
    decision_id: str | None = None,
    node_id: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """
    Return inspection results for operator console (run_id, decision_id, node_id filters).
    Resolves run_dir from run_index_db when run_id is provided.
    """
    root = _workspace_root()
    if not root:
        return {"ok": False, "error": "workspace not available", "results": []}
    try:
        from hg_core.repr_interp.api import api_repr_interp_results
    except ImportError:
        return {"ok": False, "error": "repr_interp not available", "results": []}
    run_dir = None
    if run_id:
        try:
            from ..services.run_index_db import get_run
            row = get_run(run_id)
            if row and row.get("run_dir"):
                run_dir = Path(row["run_dir"])
        except Exception:
            pass
    out = api_repr_interp_results(
        root,
        run_dir=run_dir,
        run_id=run_id,
        decision_id=decision_id,
        node_id=node_id,
        limit=limit,
    )
    return {"ok": True, "results": out.get("results", [])}


def get_proof_path_for_decision(decision_id: str) -> dict[str, Any]:
    """
    Return full proof path for a decision (decision, predictions, evaluations,
    self_assessments, representation_inspection_result). For operator console and Viz Phase 4.
    """
    root = _workspace_root()
    if not root:
        return {"ok": False, "error": "workspace not available", "proof_path": None}
    try:
        from hg_core.viz.api import get_viz_proof_path
        proof = get_viz_proof_path(root, decision_id)
        return {"ok": True, "proof_path": proof}
    except Exception as e:
        return {"ok": False, "error": str(e), "proof_path": None}
