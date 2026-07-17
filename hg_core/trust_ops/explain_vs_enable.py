# Pack 14: Explain vs enable policy (high-risk assistance)
from __future__ import annotations

from typing import Any, Dict

ASSISTANCE_MODE_EXPLAIN_ONLY = "explain-only"
ASSISTANCE_MODE_ACTION_ENABLED = "action-enabled"

ASSISTANCE_MODE_SET = "ASSISTANCE_MODE_SET"
ASSISTANCE_DENIED_BY_POLICY = "ASSISTANCE_DENIED_BY_POLICY"


def assistance_policy_decision(
    mode: str,
    action_type: str,
    policy: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Policy decision for high-risk assistance. Returns { allowed: bool, reason: str, proof_ref: str }.
    allow explain-only; require approval or deny for actionable steps in high-risk domains.
    """
    high_risk_actions = policy.get("high_risk_action_types", ["enable_harm", "weaponize", "evade_detection"])
    if mode == ASSISTANCE_MODE_EXPLAIN_ONLY:
        return {"allowed": True, "reason": "explain_only", "proof_ref": ""}
    if action_type in high_risk_actions:
        return {"allowed": False, "reason": "assistance_denied_high_risk", "proof_ref": "ASSISTANCE_DENIED_BY_POLICY"}
    if policy.get("require_approval_for_action", False):
        return {"allowed": False, "reason": "approval_required", "proof_ref": "approval_required"}
    return {"allowed": True, "reason": "allowed", "proof_ref": ""}
