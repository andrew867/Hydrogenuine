"""
Coalition safeguards (Pack 3): apply policy-driven safeguards from signals.
Emit SAFEGUARD_APPLIED with rationale; SAFEGUARD_LIFTED.
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


def apply_safeguard(
    *,
    kind: str,
    scope: Dict[str, str],
    targets: List[Dict[str, Any]],
    scope_actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    rationale: str = "",
    signal_ref: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Emit SAFEGUARD_APPLIED. Write rationale artifact.
    kind: e.g. require_independent_reviewer, force_verifier_diversity, spot_check_required,
          throttle_delegation, freeze_trust_band, block_closed_loop.
    Returns safeguard_id (event object id).
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    safeguard_id = "sg_" + hashlib.sha256(f"{kind}:{ts}".encode()).hexdigest()[:16]
    root = workspace_root / "artifacts" / "coalition" / "safeguards"
    root.mkdir(parents=True, exist_ok=True)
    rationale_path = root / f"{safeguard_id}.json"
    rationale_path.write_text(
        json.dumps({
            "safeguard_id": safeguard_id,
            "kind": kind,
            "scope": scope,
            "targets": targets,
            "rationale": rationale,
            "signal_ref": signal_ref,
            "ts": ts,
        }, indent=2),
        encoding="utf-8",
    )
    emit(
        "SAFEGUARD_APPLIED",
        "safeguard",
        safeguard_id,
        {
            "safeguard_id": safeguard_id,
            "scope": scope,
            "ts": ts,
            "kind": kind,
            "targets": targets,
            "rationale_artifact_id": str(rationale_path),
        },
        scope=scope,
        actor=scope_actor,
        workspace_root=workspace_root,
    )
    return safeguard_id


def lift_safeguard(
    *,
    safeguard_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    reason: str = "",
) -> str:
    """Emit SAFEGUARD_LIFTED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "SAFEGUARD_LIFTED",
        "safeguard",
        safeguard_id,
        {"safeguard_id": safeguard_id, "reason": reason, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def apply_safeguards_for_signal(
    signal: Dict[str, Any],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> List[str]:
    """
    Map coalition signal_type to safeguards and apply them. Returns list of safeguard_ids.
    approval_ring -> require_independent_reviewer, block_closed_loop
    verifier_monoculture -> force_verifier_diversity
    """
    workspace_root = Path(workspace_root or ".")
    signal_type = signal.get("signal_type") or ""
    targets = [{"signal_type": signal_type, "signal_ref": signal}]
    applied: List[str] = []
    if signal_type == "approval_ring":
        sg_id = apply_safeguard(
            kind="require_independent_reviewer",
            scope=scope,
            targets=targets,
            scope_actor=actor,
            workspace_root=workspace_root,
            rationale="Approval ring detected; independent reviewer required.",
            signal_ref=signal,
        )
        applied.append(sg_id)
        sg_id2 = apply_safeguard(
            kind="block_closed_loop",
            scope=scope,
            targets=targets,
            scope_actor=actor,
            workspace_root=workspace_root,
            rationale="Closed-loop approvals blocked until review.",
            signal_ref=signal,
        )
        applied.append(sg_id2)
    elif signal_type == "verifier_monoculture":
        sg_id = apply_safeguard(
            kind="force_verifier_diversity",
            scope=scope,
            targets=targets,
            scope_actor=actor,
            workspace_root=workspace_root,
            rationale="Verifier monoculture detected; require multiple independent sources.",
            signal_ref=signal,
        )
        applied.append(sg_id)
    return applied


def list_active_safeguards(
    workspace_root: Path,
    scope: Optional[Dict[str, str]] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Return SAFEGUARD_APPLIED events that have no matching SAFEGUARD_LIFTED. Most recent first."""
    from hg_core.ledger.ledger_writer import iter_events_by_scope
    lifted: set = set()
    applied_list: List[Dict[str, Any]] = []
    for _st, _sid, ev in iter_events_by_scope(Path(workspace_root)):
        if ev.get("action") == "SAFEGUARD_LIFTED":
            lifted.add((ev.get("payload") or {}).get("safeguard_id"))
        elif ev.get("action") == "SAFEGUARD_APPLIED":
            p = (ev.get("payload") or {}).copy()
            p["event_id"] = ev.get("event_id")
            p["ts"] = p.get("ts") or ev.get("ts")
            ev_scope = ev.get("scope") or p.get("scope") or {}
            if scope and ev_scope != scope:
                continue
            applied_list.append(p)
    out = [a for a in applied_list if a.get("safeguard_id") not in lifted]
    out.sort(key=lambda x: x.get("ts") or "", reverse=True)
    return out[:limit]
