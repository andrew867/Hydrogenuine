"""
Layer 9 Phase 2: Process audit for operator console.
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


def get_process_audit(decision_id: str | None = None, run_id: str | None = None) -> dict[str, Any]:
    """GET process audit by decision_id or run_id."""
    root = _workspace_root()
    if not root:
        return {"ok": False, "error": "workspace not available"}
    try:
        from hg_core.alignment_science.api import get_process_audit_api
        return get_process_audit_api(root, decision_id=decision_id, run_id=run_id)
    except ImportError:
        return {"ok": False, "error": "alignment_science not available"}


def run_process_audit(decision_id: str, run_id: str | None = None, emit_ledger: bool = True) -> dict[str, Any]:
    """POST run process audit for decision_id."""
    root = _workspace_root()
    if not root:
        return {"ok": False, "error": "workspace not available"}
    try:
        from hg_core.alignment_science.api import run_process_audit_api
        return run_process_audit_api(root, decision_id, run_id=run_id, emit_ledger=emit_ledger)
    except ImportError:
        return {"ok": False, "error": "alignment_science not available"}
