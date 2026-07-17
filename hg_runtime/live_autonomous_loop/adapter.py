"""ALOOP-LIVE runtime adapter — fake sink only; no live loop start."""

from __future__ import annotations

from typing import Any

from hg_core.aloop_live.config import aloop_fake_sink_only, aloop_refuse_live_loop_start
from hg_core.aloop_live.errors import ALOOP_FAKE_SINK, REFUSED_LIVE_LOOP_START
from hg_core.aloop_live.no_authority import advisory_only_marker
from hg_runtime.live_autonomous_loop.types import FIXTURE_CLOCK, LoopLease, LoopSupervisorReceipt


def lease_to_fake_sink(
    lease: LoopLease,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    """Stage loop lease in fake sink; never starts live loop."""
    if not aloop_fake_sink_only():
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": "aloop.refused.fake_sink_disabled",
            "live_loop_started": False,
        }

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "aloop.advisory.lease_staged",
        "sink_type": "fake",
        "lease_ref": lease.lease_id,
        "loop_scope": lease.loop_scope,
        "live_loop_started": False,
        "loop_self_renewed": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


def supervise_to_fake_sink(
    receipt: LoopSupervisorReceipt,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    """Commit supervisor receipt to fake sink; never starts live loop."""
    if not aloop_refuse_live_loop_start():
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_LIVE_LOOP_START,
            "live_loop_started": False,
        }

    if not aloop_fake_sink_only():
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": "aloop.refused.fake_sink_disabled",
            "live_loop_started": False,
        }

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": ALOOP_FAKE_SINK,
        "sink_type": "fake",
        "receipt_ref": receipt.receipt_id,
        "supervisor_state": receipt.supervisor_state,
        "live_loop_started": False,
        "loop_self_renewed": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


__all__ = ["lease_to_fake_sink", "supervise_to_fake_sink"]
