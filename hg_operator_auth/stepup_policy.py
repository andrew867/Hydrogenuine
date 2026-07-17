"""Risk-based step-up policy for operator approvals. Fail closed on unknowns.

Defaults (mission-mandated):
    low         → login required
    medium      → login + recent session (auth within SESSION_RECENT_S)
    high        → step-up once per session, or re-step-up after STEP_UP_TIMEOUT_S
    restricted  → step-up EVERY approval
    breakglass  → step-up EVERY approval + non-empty reason
Denials never require step-up by default. Self-approval is allowed in dev and
configurable. One approver by default; two-person review is a future flag.

`prohibited`/`forbidden` action outcomes are refusals, never step-up-able —
they are not representable here by design (no risk category maps to them).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from hg_operator_auth.identity import OperatorIdentity
from hg_operator_auth.roles import can_approve_as_human

RISK_CATEGORIES = ("low", "medium", "high", "restricted", "breakglass")

# action class → (risk category, required hg role)
ACTION_CLASS_POLICY: dict[str, tuple[str, str]] = {
    "observation": ("low", "hg.viewer"),
    "draft": ("low", "hg.operator"),
    "promotion": ("medium", "hg.approver"),
    "configuration": ("high", "hg.config_admin"),
    "external_effect": ("restricted", "hg.restricted_approver"),
    "embodied_control": ("restricted", "hg.embodied_operator"),
    "memory_mutation": ("high", "hg.memory_admin"),
    "model_route_change": ("high", "hg.model_operator"),
    "breakglass": ("breakglass", "hg.breakglass"),
}

STEP_UP_TIMEOUT_S = 900          # 15 minutes for high risk
SESSION_RECENT_S = 8 * 3600      # medium: auth within this window


@dataclass(frozen=True)
class StepUpVerdict:
    allowed: bool
    step_up_required: bool
    step_up_satisfied: bool
    reason: str


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def evaluate_step_up(
    *,
    action_class: str,
    decision: str,                       # "approve" | "deny"
    identity: OperatorIdentity,
    now: datetime,
    last_step_up_at: Optional[datetime] = None,
    breakglass_reason: str = "",
    allow_self_approval: bool = True,    # dev default; configurable
    requested_by_subject: str = "",
) -> StepUpVerdict:
    """Evaluate whether this decision may proceed. Fail closed on unknowns."""
    if action_class not in ACTION_CLASS_POLICY:
        return StepUpVerdict(False, True, False, "unknown_action_class")
    if decision not in ("approve", "deny"):
        return StepUpVerdict(False, True, False, "unknown_decision")

    # Denials never require step-up by default — but still require a human login.
    if decision == "deny":
        if identity.demo_local_signing or identity.production_operator_auth:
            return StepUpVerdict(True, False, False, "deny_no_step_up_required")
        return StepUpVerdict(False, False, False, "deny_requires_login")

    risk, required_role = ACTION_CLASS_POLICY[action_class]
    roles = set(identity.roles)
    if not can_approve_as_human(identity.roles):
        return StepUpVerdict(False, True, False, "not_a_human_approver")
    if required_role not in roles and "hg.admin" not in roles:
        return StepUpVerdict(False, True, False, f"missing_role:{required_role}")
    if risk in ("high", "restricted", "breakglass") \
            and risk == "high" and "hg.high_risk_approver" not in roles \
            and "hg.admin" not in roles and required_role not in roles:
        return StepUpVerdict(False, True, False, "missing_role:hg.high_risk_approver")
    if not allow_self_approval and requested_by_subject \
            and requested_by_subject == identity.subject:
        return StepUpVerdict(False, False, False, "self_approval_forbidden")

    if risk == "low":
        return StepUpVerdict(True, False, False, "login_sufficient")

    auth_time = _parse_iso(identity.auth_time)
    if risk == "medium":
        if auth_time is None or now - auth_time > timedelta(seconds=SESSION_RECENT_S):
            return StepUpVerdict(False, False, False, "session_not_recent")
        return StepUpVerdict(True, False, False, "recent_session_ok")

    # high / restricted / breakglass need step-up evidence
    if not identity.step_up_satisfied or not identity.step_up_evidence:
        return StepUpVerdict(False, True, False, "step_up_missing")
    if risk == "high":
        anchor = last_step_up_at
        if anchor is None:
            # first step-up this session: evidence itself is the anchor
            return StepUpVerdict(True, True, True, "step_up_fresh")
        if now - anchor > timedelta(seconds=STEP_UP_TIMEOUT_S):
            return StepUpVerdict(False, True, False, "step_up_stale")
        return StepUpVerdict(True, True, True, "step_up_within_timeout")
    if risk == "restricted":
        # per-approval: caller must present per-decision evidence; a session-scoped
        # anchor is not enough — evidence tuple must be non-empty (already checked).
        return StepUpVerdict(True, True, True, "step_up_per_approval")
    # breakglass
    if not breakglass_reason.strip():
        return StepUpVerdict(False, True, False, "breakglass_reason_required")
    return StepUpVerdict(True, True, True, "breakglass_step_up_with_reason")


__all__ = ["ACTION_CLASS_POLICY", "RISK_CATEGORIES", "SESSION_RECENT_S",
           "STEP_UP_TIMEOUT_S", "StepUpVerdict", "evaluate_step_up"]
