"""
Anchor service: publish Merkle root for a scope range; verify by recomputing.
ANCHOR_PUBLISHED, ANCHOR_VERIFIED; anchor artifacts under artifacts/integrity/anchors/.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit
from hg_core.ledger.ledger_writer import iterate_events
from .merkle import merkle_root, compute_merkle_root_for_range


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _anchor_artifact_path(workspace_root: Path, anchor_id: str) -> Path:
    return Path(workspace_root) / "artifacts" / "integrity" / "anchors" / f"{anchor_id}.json"


def publish_anchor(
    *,
    workspace_root: Path,
    scope_type: str,
    scope_id: str,
    from_event_id: str,
    to_event_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    tenant_id: Optional[str] = None,
    environment: Optional[str] = None,
) -> str:
    """
    Compute Merkle root for events in scope in [from_event_id, to_event_id], write anchor artifact, emit ANCHOR_PUBLISHED.
    Returns anchor_id.
    """
    workspace_root = Path(workspace_root)
    event_ids: List[str] = []
    for ev in iterate_events(
        workspace_root,
        scope_type=scope_type,
        scope_id=scope_id,
        tenant_id=tenant_id,
        environment=environment,
    ):
        eid = ev.get("event_id")
        if eid:
            event_ids.append(eid)
    in_range_ids: List[str] = []
    started = False
    for eid in event_ids:
        if eid == from_event_id:
            started = True
        if started:
            in_range_ids.append(eid)
        if started and eid == to_event_id:
            break
    root = merkle_root(in_range_ids)
    ts = _iso_ts()
    anchor_id = "anc_" + hashlib.sha256(f"{scope_type}:{scope_id}:{ts}:{root}".encode()).hexdigest()[:16]
    scope_ref = {"type": scope_type, "id": scope_id}
    range_payload = {"from_event_id": from_event_id, "to_event_id": to_event_id}
    artifact = {
        "anchor_id": anchor_id,
        "scope_ref": scope_ref,
        "merkle_root": root,
        "range": range_payload,
        "ts": ts,
        "event_count": len(in_range_ids),
        "event_ids": in_range_ids[:100],
    }
    art_path = _anchor_artifact_path(workspace_root, anchor_id)
    art_path.parent.mkdir(parents=True, exist_ok=True)
    art_path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8")
    emit(
        "ANCHOR_PUBLISHED",
        "anchor",
        anchor_id,
        {
            "anchor_id": anchor_id,
            "scope_ref": scope_ref,
            "merkle_root": root,
            "range": range_payload,
            "ts": ts,
            "anchor_artifact_id": str(art_path),
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return anchor_id


def verify_anchor(
    *,
    workspace_root: Path,
    anchor_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
) -> Dict[str, Any]:
    """
    Load anchor artifact, recompute Merkle root for the range, compare. Emit ANCHOR_VERIFIED.
    Returns {ok: bool, expected_root: str, computed_root: str, anchor_id: str}.
    """
    workspace_root = Path(workspace_root)
    art_path = _anchor_artifact_path(workspace_root, anchor_id)
    if not art_path.exists():
        emit(
            "ANCHOR_VERIFIED",
            "anchor",
            anchor_id,
            {"anchor_id": anchor_id, "ts": _iso_ts(), "result": "missing_artifact", "ok": False},
            scope=scope,
            actor=actor,
            workspace_root=workspace_root,
        )
        return {"ok": False, "anchor_id": anchor_id, "error": "missing_artifact"}
    data = json.loads(art_path.read_text(encoding="utf-8"))
    scope_ref = data.get("scope_ref") or {}
    st = scope_ref.get("type", "run")
    sid = scope_ref.get("id", "default")
    rng = data.get("range") or {}
    from_id = rng.get("from_event_id", "")
    to_id = rng.get("to_event_id", "")
    event_ids: List[str] = []
    for ev in iterate_events(workspace_root, scope_type=st, scope_id=sid):
        eid = ev.get("event_id")
        if eid:
            event_ids.append(eid)
    computed = compute_merkle_root_for_range(event_ids, from_id, to_id)
    expected = data.get("merkle_root", "")
    ok = computed == expected
    verifier_artifact = {"anchor_id": anchor_id, "ok": ok, "expected_root": expected, "computed_root": computed}
    ver_path = workspace_root / "artifacts" / "integrity" / "verifications" / f"{anchor_id}.json"
    ver_path.parent.mkdir(parents=True, exist_ok=True)
    ver_path.write_text(json.dumps(verifier_artifact, indent=2), encoding="utf-8")
    emit(
        "ANCHOR_VERIFIED",
        "anchor",
        anchor_id,
        {"anchor_id": anchor_id, "ts": _iso_ts(), "result": "ok" if ok else "mismatch", "ok": ok, "verifier_artifact_id": str(ver_path)},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return {"ok": ok, "anchor_id": anchor_id, "expected_root": expected, "computed_root": computed}
