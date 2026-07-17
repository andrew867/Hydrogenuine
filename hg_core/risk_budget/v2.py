"""
Risk budget v2 (Pack 4): fan-out, blast radius, verifier diversity, continuity, gap, regret, constraint violation.
RISK_COST_COMPUTED with rationale artifact; required_controls.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from hg_core.ledger import emit

INFINITE_COST = 1e12


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def compute_risk_cost_v2(
    *,
    fan_out: float = 1.0,
    blast_radius: float = 0.0,
    verifier_diversity_quality: float = 1.0,
    continuity_invalidations: int = 0,
    gap_score: float = 0.0,
    regret: float = 0.0,
    constraint_violation: bool = False,
) -> Tuple[float, Dict[str, Any]]:
    """
    Compute risk cost v2 and required controls.
    constraint_violation=True (hard constraint) -> infinite cost unless exception.
    Returns (cost, required_controls).
    """
    if constraint_violation:
        return INFINITE_COST, {
            "min_evidence_count": 2,
            "min_robustness_threshold": 1.0,
            "independent_reviewer_required": True,
            "escrow_or_stake_required": True,
            "step_size_limits": "scope_reduction",
        }
    base = max(1.0, fan_out) * (1.0 + max(0.0, min(1.0, blast_radius)))
    div_mult = 2.0 - max(0.0, min(1.0, verifier_diversity_quality))
    cont_add = continuity_invalidations * 0.5
    gap_mult = 1.0 + max(0.0, min(1.0, gap_score)) * 0.5
    regret_mult = 1.0 + max(0.0, min(1.0, regret)) * 0.3
    cost = base * div_mult * gap_mult * regret_mult + cont_add
    cost = round(min(cost, INFINITE_COST - 1), 2)
    required_controls: Dict[str, Any] = {}
    if verifier_diversity_quality < 0.5:
        required_controls["min_evidence_count"] = 2
        required_controls["independent_reviewer_required"] = True
    if continuity_invalidations > 0:
        required_controls["min_robustness_threshold"] = 0.7
    if gap_score > 0.5:
        required_controls["step_size_limits"] = "scope_reduction"
    return cost, required_controls


def emit_risk_cost_computed(
    *,
    action_id: str,
    work_item_id: str,
    cost: float,
    components: Dict[str, Any],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    required_controls: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str]:
    """Write rationale artifact and emit RISK_COST_COMPUTED. Returns (risk_id, event_id)."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    risk_id = "risk_" + hashlib.sha256(f"{action_id}:{work_item_id}:{ts}".encode()).hexdigest()[:16]
    root = workspace_root / "artifacts" / "risk"
    root.mkdir(parents=True, exist_ok=True)
    rationale_path = root / f"{risk_id}.json"
    rationale_path.write_text(
        json.dumps({
            "risk_id": risk_id,
            "action_id": action_id,
            "work_item_id": work_item_id,
            "cost": cost,
            "components": components,
            "required_controls": required_controls or {},
            "ts": ts,
        }, indent=2),
        encoding="utf-8",
    )
    payload = {
        "risk_id": risk_id,
        "action_id": action_id,
        "work_item_id": work_item_id,
        "cost": cost,
        "ts": ts,
        "components": components,
        "rationale_artifact_id": str(rationale_path),
    }
    ev_id = emit(
        "RISK_COST_COMPUTED",
        "risk",
        risk_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return risk_id, ev_id
