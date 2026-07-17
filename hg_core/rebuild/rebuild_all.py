"""
OS Phase 1: Rebuild all materializers and produce hash manifest for derived views.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.materializers import run_all
from hg_core.materializers._checkpoint import get_materialized_root


def get_hash_manifest(workspace_root: Path) -> Dict[str, str]:
    """Compute SHA-256 hash of each file in memory/materialized (excluding checkpoints if desired). Return {relative_path: hex_hash}."""
    workspace_root = Path(workspace_root)
    root = get_materialized_root(workspace_root)
    manifest: Dict[str, str] = {}
    if not root.exists():
        return manifest
    for f in sorted(root.glob("*.jsonl")):
        try:
            data = f.read_bytes()
            manifest[f.name] = hashlib.sha256(data).hexdigest()
        except Exception:
            continue
    return manifest


def rebuild_with_manifest(workspace_root: Path, rebuild: bool = True) -> Dict[str, Any]:
    """Run all materializers (optionally rebuild=True), then compute hash manifest. Returns summary with ok, manifest, message."""
    workspace_root = Path(workspace_root)
    if rebuild:
        run_all(workspace_root, rebuild=True)
    manifest = get_hash_manifest(workspace_root)
    return {"ok": True, "message": "rebuild completed", "manifest": manifest}
