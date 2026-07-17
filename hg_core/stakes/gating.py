"""
Gating middleware: check agency_budget, trust_band, escrow before allowing action.
Emits APPROVAL_REQUESTED and blocks or allows; records allow/deny/rate_limit as ledger events (caller responsibility).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .policy import load_policy, get_action_cost, get_trust_band_limits


@dataclass
class GateResult:
    allowed: bool
    reason: str
    approval_required: bool = False
    rate_limit: bool = False


def check_gate(
    action: str,
    agent_id: str,
    current_budget_used: float,
    trust_band: int,
    escrow_locked: float,
    policy: Optional[Dict[str, Any]] = None,
    workspace_root: Optional[Path] = None,
    decision_id: Optional[str] = None,
    run_id: Optional[str] = None,
) -> GateResult:
    """
    Check if action is allowed given budget, trust band, and policy.
    When policy has process_legible_required or process_score_min and decision_id is provided,
    requires ProcessAuditResult with legible=true or score >= min (Layer 9 Phase 2).
    Returns GateResult(allowed, reason, approval_required, rate_limit).
    """
    policy = policy or load_policy(workspace_root)
    cost = get_action_cost(policy, action)
    budget_cfg = policy.get("budget") or {}
    limit = float(budget_cfg.get("default_limit", 100.0))
    hard = bool(budget_cfg.get("hard", True))
    band_limits = get_trust_band_limits(policy)
    max_action = band_limits.get(trust_band)
    if max_action is not None and action != max_action:
        # Simple check: if action is "higher" than band allows, require approval or deny
        order = ["READ", "WRITE", "DECISION_PROPOSED", "DECISION_COMMITTED"]
        try:
            ai = order.index(action) if action in order else 999
            mi = order.index(max_action) if max_action in order else -1
            if ai > mi:
                return GateResult(False, "trust_band_insufficient", approval_required=True, rate_limit=False)
        except ValueError:
            pass
    if current_budget_used + cost > limit:
        if hard:
            return GateResult(False, "budget_exceeded", approval_required=False, rate_limit=False)
        return GateResult(True, "over_budget_soft", approval_required=True, rate_limit=True)

    # Layer 9 Phase 2: process_legible_required or process_score_min (when decision_id provided)
    if decision_id and workspace_root:
        process_legible_required = policy.get("process_legible_required") is True
        process_score_min = policy.get("process_score_min")
        if process_legible_required or process_score_min is not None:
            try:
                from hg_core.alignment_science.process_audit import get_process_audit
                audit = get_process_audit(Path(workspace_root), decision_id)
                if audit is None:
                    return GateResult(False, "process_audit_missing", approval_required=True, rate_limit=False)
                if process_legible_required and not audit.get("legible"):
                    return GateResult(False, "process_not_legible", approval_required=True, rate_limit=False)
                if process_score_min is not None:
                    min_val = float(process_score_min)
                    score = audit.get("process_compliance_score")
                    if score is None or float(score) < min_val:
                        return GateResult(False, "process_score_below_min", approval_required=True, rate_limit=False)
            except Exception:
                return GateResult(False, "process_audit_check_failed", approval_required=True, rate_limit=False)

    return GateResult(True, "ok", approval_required=False, rate_limit=False)
