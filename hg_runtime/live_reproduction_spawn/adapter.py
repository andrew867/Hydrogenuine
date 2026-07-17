"""RIB-SPAWN-LIVE runtime adapter — fake sink only; no live spawn."""

from __future__ import annotations

from typing import Any

from hg_core.rib_spawn_live.config import rib_spawn_fake_sink_only, rib_spawn_refuse_live_spawn
from hg_core.rib_spawn_live.errors import REFUSED_LIVE_SPAWN, RIB_SPAWN_FAKE_SINK
from hg_core.rib_spawn_live.no_authority import advisory_only_marker
from hg_runtime.live_reproduction_spawn.types import FIXTURE_CLOCK, ChildIdentityProfile, ChildSpawnReceipt


def plan_to_fake_sink(
    identity: ChildIdentityProfile,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    """Stage spawn plan in fake sink; never performs live spawn."""
    if not rib_spawn_fake_sink_only():
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": "rib_spawn.refused.fake_sink_disabled",
            "live_spawn_performed": False,
        }

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "rib_spawn.advisory.plan_staged",
        "sink_type": "fake",
        "child_iam_ref": identity.child_iam_ref,
        "parent_iam_ref": identity.parent_iam_ref,
        "live_spawn_performed": False,
        "child_inherits_authority": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


def commit_to_fake_sink(
    receipt: ChildSpawnReceipt,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    """Commit spawn receipt to fake sink; never performs live spawn."""
    if not rib_spawn_refuse_live_spawn():
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_LIVE_SPAWN,
            "live_spawn_performed": False,
        }

    if not rib_spawn_fake_sink_only():
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": "rib_spawn.refused.fake_sink_disabled",
            "live_spawn_performed": False,
        }

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": RIB_SPAWN_FAKE_SINK,
        "sink_type": "fake",
        "receipt_ref": receipt.receipt_id,
        "child_iam_ref": receipt.child_iam_ref,
        "live_spawn_performed": False,
        "child_inherits_authority": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


__all__ = ["commit_to_fake_sink", "plan_to_fake_sink"]
