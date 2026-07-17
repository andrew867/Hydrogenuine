"""SRP-LIVE runtime adapter — fake sink only; plan/apply separation."""

from __future__ import annotations

from typing import Any

from hg_core.policy_safety.hashing import canonical_hash
from hg_core.srp_live.config import srp_fake_sink_only
from hg_core.srp_live.errors import SRP_COMMIT_FAKE_SINK, SRP_PLAN_BOUND
from hg_core.srp_live.no_authority import advisory_only_marker
from hg_runtime.live_srp_apply.types import FIXTURE_CLOCK, SRPApplyPlan, SRPApplyReceipt, SRPApplyRequest


def _plan_id(repair_id: str) -> str:
    digest = canonical_hash({"repair_id": repair_id, "phase": "plan"})
    return f"srp-plan-{digest.rsplit(':', 1)[-1][:12]}"


def plan_to_operator_visible(
    request: SRPApplyRequest,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    """Build operator-visible apply plan without landing — plan phase only."""
    plan = SRPApplyPlan(
        plan_id=_plan_id(request.repair_id),
        repair_id=request.repair_id,
        phase="plan",
        pre_checks=("iam_binding", "tim_freshness", "approval_window", "digest_match"),
        apply_steps=("stage_fake_sink", "verify_digest", "record_receipt"),
        verify_steps=("digest_equals_approved", "rollback_registered"),
        abort_points=("pre_check_fail", "verify_fail", "panic_lockdown"),
        operator_visible=True,
    )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": SRP_PLAN_BOUND,
        "phase": "plan",
        "plan": plan.to_payload(),
        "request_ref": request.repair_id,
        "srp_apply_called": False,
        "live_landing_performed": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


def apply_to_fake_sink(
    receipt: SRPApplyReceipt,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    """Apply SRP repair to fake sink; never performs live landing."""
    if not srp_fake_sink_only():
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": "srp.refused.fake_sink_disabled",
            "live_landing_performed": False,
        }

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": SRP_COMMIT_FAKE_SINK,
        "sink_type": "fake",
        "phase": "apply",
        "receipt_ref": receipt.receipt_id,
        "repair_id": receipt.repair_id,
        "applied_digest": receipt.applied_digest,
        "live_landing_performed": False,
        "srp_apply_called": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


__all__ = ["apply_to_fake_sink", "plan_to_operator_visible"]
