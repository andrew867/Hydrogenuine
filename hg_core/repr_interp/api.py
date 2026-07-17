"""
Layer 8 Phase 3: Read-only API for representation interpretability inspection results.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.repr_interp.storage import get_inspection_results


def api_repr_interp_results(
    workspace_root: Path,
    run_dir: Optional[Path] = None,
    run_id: Optional[str] = None,
    decision_id: Optional[str] = None,
    node_id: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """
    Read-only API: return inspection results for proof-path and operator console.
    Returns { results: [...] } with optional limit.
    """
    workspace_root = Path(workspace_root)
    results = get_inspection_results(
        workspace_root,
        run_dir=run_dir,
        run_id=run_id,
        decision_id=decision_id,
        node_id=node_id,
    )
    if limit > 0:
        results = results[-limit:]
    return {"results": results}
