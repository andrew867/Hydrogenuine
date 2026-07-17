"""
OS Phase 1: CI manifest drift check. Compare current rebuild manifest to golden (or saved) manifest.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .rebuild_all import rebuild_with_manifest, get_hash_manifest


def check_manifest_drift(
    workspace_root: Path,
    expected_manifest_path: Optional[Path] = None,
    expected_manifest: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Rebuild, get current manifest, compare to expected (from file or dict).
    Returns: ok (bool), drift (list of {file, expected_hash, actual_hash}), message.
    """
    workspace_root = Path(workspace_root)
    result = rebuild_with_manifest(workspace_root, rebuild=True)
    current = result.get("manifest") or {}
    if expected_manifest is not None:
        expected = expected_manifest
    elif expected_manifest_path is not None:
        path = Path(expected_manifest_path)
        if not path.exists():
            return {"ok": False, "drift": [], "message": "expected_manifest_path not found"}
        with open(path, encoding="utf-8") as f:
            expected = json.load(f)
    else:
        expected = {}
    drift: List[Dict[str, Any]] = []
    all_keys = set(current) | set(expected)
    for k in sorted(all_keys):
        cur = current.get(k)
        exp = expected.get(k)
        if cur != exp:
            drift.append({"file": k, "expected_hash": exp, "actual_hash": cur})
    return {
        "ok": len(drift) == 0,
        "drift": drift,
        "message": "no drift" if not drift else f"{len(drift)} file(s) drifted",
    }
