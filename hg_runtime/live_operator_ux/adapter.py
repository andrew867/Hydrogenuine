"""OUX-LIVE runtime adapter — fake sink only; no live external action."""

from __future__ import annotations

from typing import Any

from hg_core.oux_live.config import oux_refuse_live_external_action
from hg_core.oux_live.no_authority import advisory_only_marker
from hg_runtime.live_operator_ux.types import FIXTURE_CLOCK, OperatorUXReceipt


def dispatch_to_fake_sink(
    receipt: OperatorUXReceipt,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    """Route operator UX receipt to fake sink; never performs live external action."""
    if not oux_refuse_live_external_action():
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": "oux.refused.live_external_action_disabled",
            "live_action_performed": False,
        }

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "oux.advisory.fake_sink_recorded",
        "sink_type": "fake",
        "receipt_ref": receipt.receipt_id,
        "control_kind": receipt.control_kind,
        "live_action_performed": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


__all__ = ["dispatch_to_fake_sink"]
