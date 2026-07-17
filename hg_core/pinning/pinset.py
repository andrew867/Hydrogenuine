"""
Pack 6: Pinset - pin versions at run start. PINSET_PUBLISHED, PINSET_APPLIED.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def publish_pinset(
    *,
    components: List[Dict[str, Any]],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Publish pinset artifact and emit PINSET_PUBLISHED. Returns pinset_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    pinset_id = "pin_" + hashlib.sha256(f"{ts}:{len(components)}".encode()).hexdigest()[:16]
    root = workspace_root / "artifacts" / "pinning"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{pinset_id}.json"
    doc = {"pinset_id": pinset_id, "ts": ts, "components": components}
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    emit(
        "PINSET_PUBLISHED",
        "pinset",
        pinset_id,
        {"pinset_id": pinset_id, "artifact_id": str(path), "ts": ts, "components_count": len(components)},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return pinset_id


def apply_pinset(
    *,
    pinset_id: str,
    run_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit PINSET_APPLIED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "PINSET_APPLIED",
        "pinset",
        pinset_id,
        {"pinset_id": pinset_id, "run_id": run_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def resolve_pinset(workspace_root: Path, pinset_id: str) -> Optional[Dict[str, Any]]:
    """Load pinset from artifacts/pinning/{pinset_id}.json."""
    path = workspace_root / "artifacts" / "pinning" / f"{pinset_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
