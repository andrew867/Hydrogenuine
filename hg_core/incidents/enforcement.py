"""
Incident enforcement: apply trust/budget/tool restrictions and record autonomy restore.
Emits ENFORCEMENT_APPLIED (effects + rationale artifact) and AUTONOMY_RESTORED (after postmortem).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from hg_core.ledger import emit


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_enforcement_rationale(workspace_root: Path, enforcement_id: str, incident_id: str, effects: Dict[str, Any], notes: str) -> str:
    root = Path(workspace_root) / "artifacts" / "enforcement"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{enforcement_id}.json"
    obj = {"enforcement_id": enforcement_id, "incident_id": incident_id, "effects": effects, "notes": notes, "ts": _iso_ts()}
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)


def apply_enforcement(
    *,
    incident_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    effects: Dict[str, Any],
    notes: str = "",
    workspace_root: Optional[Path] = None,
) -> str:
    """
    Emit ENFORCEMENT_APPLIED: what changed (trust band, budgets, tool allowlist, approval thresholds, modulations).
    Writes rationale artifact to artifacts/enforcement/<enforcement_id>.json.
    Returns enforcement_id.
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    enforcement_id = "enf_" + hashlib.sha256(f"{incident_id}:{ts}".encode()).hexdigest()[:16]
    rationale_path = _write_enforcement_rationale(workspace_root, enforcement_id, incident_id, effects, notes)
    payload = {
        "enforcement_id": enforcement_id,
        "incident_id": incident_id,
        "scope": scope,
        "ts": ts,
        "effects": effects,
        "rationale_artifact_id": rationale_path,
    }
    emit(
        "ENFORCEMENT_APPLIED",
        "enforcement",
        enforcement_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return enforcement_id


def record_autonomy_restored(
    *,
    incident_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    postmortem_ref: str,
    workspace_root: Optional[Path] = None,
) -> str:
    """
    Emit AUTONOMY_RESTORED after postmortem gate (medium+ severity requires postmortem before restore).
    Returns event_id.
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    payload = {"incident_id": incident_id, "postmortem_ref": postmortem_ref, "ts": ts}
    return emit(
        "AUTONOMY_RESTORED",
        "autonomy_restore",
        incident_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
