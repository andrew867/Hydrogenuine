"""
Regulatory override: REGULATORY_OVERRIDE_APPLIED with expiry and rationale; revoke emits revoke event.
Overrides must have hard expiry; no path for indefinite or unaudited overrides.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from hg_core.ledger import emit
from .artifacts import write_override_rationale


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def apply_regulatory_override(
    *,
    scope: Dict[str, str],
    actor: Dict[str, str],
    override_spec: Dict[str, Any],
    expiry_ts: str,
    rationale: str,
    workspace_root: Optional[Path] = None,
) -> str:
    """
    Emit REGULATORY_OVERRIDE_APPLIED. rationale required; expiry_ts required (hard expiry).
    override_spec describes what is overridden (e.g. allow_action, trust_band_override). Returns override_id.
    """
    workspace_root = Path(workspace_root or ".")
    if not rationale:
        raise ValueError("rationale required for regulatory override")
    if not expiry_ts:
        raise ValueError("expiry_ts required for regulatory override")
    ts = _iso_ts()
    override_id = hashlib.sha256(f"{ts}:{override_spec!r}:{expiry_ts}".encode()).hexdigest()
    write_override_rationale(
        workspace_root,
        override_id,
        {"override_id": override_id, "ts": ts, "override_spec": override_spec, "expiry_ts": expiry_ts, "rationale": rationale},
    )
    emit(
        "REGULATORY_OVERRIDE_APPLIED",
        "regulatory_override",
        override_id,
        {
            "override_id": override_id,
            "ts": ts,
            "override_spec": override_spec,
            "expiry_ts": expiry_ts,
            "rationale_artifact_id": override_id,
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return override_id


def revoke_regulatory_override(
    override_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    reason: str,
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit REGULATORY_OVERRIDE_REVOKED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "REGULATORY_OVERRIDE_REVOKED",
        "regulatory_override",
        override_id,
        {"override_id": override_id, "reason": reason, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
