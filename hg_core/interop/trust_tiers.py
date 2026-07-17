"""
Interop Pack 2: Trust tiers — negotiation, downgrade blocking, time-bound exception.
TRUST_TIER_PROPOSED, TRUST_TIER_ACCEPTED, TRUST_TIER_REJECTED, TRUST_TIER_DOWNGRADE_EXCEPTION_GRANTED.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from hg_core.ledger import emit


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


TIER_ORDER = ("T0", "T1", "T2", "T3")


def propose_trust_tier(
    *,
    tier: str,
    ref_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """Emit TRUST_TIER_PROPOSED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "TRUST_TIER_PROPOSED",
        "trust_tier",
        ref_id,
        {"tier": tier, "ref_id": ref_id, "context": context or {}, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def accept_trust_tier(
    *,
    ref_id: str,
    tier: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit TRUST_TIER_ACCEPTED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "TRUST_TIER_ACCEPTED",
        "trust_tier",
        ref_id,
        {"ref_id": ref_id, "tier": tier, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def reject_trust_tier(
    *,
    ref_id: str,
    reason: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit TRUST_TIER_REJECTED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "TRUST_TIER_REJECTED",
        "trust_tier",
        ref_id,
        {"ref_id": ref_id, "reason": reason, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def grant_downgrade_exception(
    *,
    ref_id: str,
    from_tier: str,
    to_tier: str,
    expiry_ts: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit TRUST_TIER_DOWNGRADE_EXCEPTION_GRANTED (time-bound). Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "TRUST_TIER_DOWNGRADE_EXCEPTION_GRANTED",
        "trust_tier",
        ref_id,
        {"ref_id": ref_id, "from_tier": from_tier, "to_tier": to_tier, "expiry_ts": expiry_ts, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def is_downgrade(from_tier: str, to_tier: str) -> bool:
    """Return True if to_tier is lower than from_tier."""
    try:
        return TIER_ORDER.index(to_tier) < TIER_ORDER.index(from_tier)
    except (ValueError, AttributeError):
        return False
