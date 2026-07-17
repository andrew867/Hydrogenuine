"""ELS startup posture selection — deterministic."""

from __future__ import annotations

from typing import Literal

from hg_runtime.emergence.types import ReadinessCheck, StartupPosture, WakeProfile

from hg_runtime.emergence.readiness import ReadinessContext


def select_posture(
    *,
    profile: WakeProfile,
    checks: list[ReadinessCheck],
    verdict: str,
    ctx: ReadinessContext,
) -> StartupPosture:
    if ctx.panic_active:
        return "SAFE_MODE"
    if ctx.lockdown_active:
        return "LOCKDOWN"
    if verdict == "safe_mode":
        return "SAFE_MODE"
    if verdict == "refused":
        return "OFFLINE_REPLAY_ONLY"
    if verdict == "failed":
        return "OFFLINE_REPLAY_ONLY"

    if profile.profile_id == "maintenance_subagent":
        return "MAINTENANCE_ONLY"

    if profile.profile_id == "live_cognition_worker":
        if not ctx.live_cognition or not ctx.live_provider_ok:
            return "PROPOSAL_ONLY"
        return "PROPOSAL_ONLY"  # readiness means can propose, not act

    if profile.profile_id == "oea_capability_worker":
        if ctx.oea_real and not ctx.oea_available:
            return "OBSERVE_ONLY"
        return "OBSERVE_ONLY"

    if profile.profile_id == "plt_operator_surface":
        return "OBSERVE_ONLY"

    degraded = any(c.status == "degraded" for c in checks)
    replay_fail = any(
        c.check_id == "replay_verified_or_refused" and c.status == "fail" for c in checks
    )
    if replay_fail:
        return "SAFE_MODE"
    if degraded or verdict == "degraded_ready":
        return "DEGRADED"
    if profile.is_subagent:
        return "OBSERVE_ONLY"
    return "NORMAL"


__all__ = ["select_posture"]
