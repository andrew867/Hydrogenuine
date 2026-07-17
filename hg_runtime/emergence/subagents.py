"""ELS sub-agent activation helpers."""

from __future__ import annotations

from typing import Any

from hg_runtime.contract import stable_id
from hg_runtime.emergence import rtc_bridge as bridge
from hg_runtime.emergence.config import ELSConfig
from hg_runtime.emergence.profiles import get_profile
from hg_runtime.emergence.readiness import ReadinessContext, run_all_checks
from hg_runtime.emergence.types import SubAgentDeclaration, SubAgentReadiness, WakeRequest


def run_subagent_wake(
    *,
    config: ELSConfig,
    declaration: SubAgentDeclaration,
    profile_id: str,
    bus: Any,
    runtime_dir: Any,
    clock_now: str,
    panic_active: bool = False,
) -> tuple[list[dict[str, Any]], SubAgentReadiness]:
    wake_id = stable_id("els_sub", declaration.agent_id, profile_id, clock_now)
    profile = get_profile(profile_id)
    drafts: list[dict[str, Any]] = []

    drafts.append(bridge.subagent_declared(wake_id, declaration))
    drafts.append(bridge.subagent_identity_bound(wake_id, declaration))

    if not declaration.scope and profile.require_scope:
        readiness = SubAgentReadiness(
            agent_id=declaration.agent_id,
            final_state="SUBAGENT_REFUSED",
            ready=False,
            refusal_reason="SCOPE_MISSING",
            posture="OBSERVE_ONLY",
        )
        drafts.append(bridge.subagent_refused(wake_id, readiness))
        return drafts, readiness

    drafts.append(bridge.subagent_scope_bound(wake_id, declaration))

    ctx = ReadinessContext(
        runtime_dir=runtime_dir,
        bus=bus,
        agent_id=declaration.agent_id,
        operator_id=None,
        scope=declaration.scope,
        panic_active=panic_active,
        lockdown_active=False,
        memory_available=True,
        oea_real=False,
        oea_available=True,
        live_cognition=False,
        live_provider_ok=False,
        secrets_redaction=True,
        stale_scratch=False,
        crr_recovery_marker=False,
        crr_snapshot_hash=None,
        expected_world_state_hash=None,
        clock_now=clock_now,
    )
    checks = run_all_checks(profile, ctx)
    failed = [c for c in checks if c.required_for_profile and c.status == "fail"]
    if failed or panic_active:
        reason = "PANIC_ACTIVE" if panic_active else (failed[0].reason_code or "CHECK_FAILED")
        readiness = SubAgentReadiness(
            agent_id=declaration.agent_id,
            final_state="SUBAGENT_REFUSED",
            ready=False,
            refusal_reason=reason,
            posture="OBSERVE_ONLY",
        )
        drafts.append(bridge.subagent_refused(wake_id, readiness))
        return drafts, readiness

    drafts.append(bridge.subagent_context_loaded(wake_id, declaration))
    readiness = SubAgentReadiness(
        agent_id=declaration.agent_id,
        final_state="SUBAGENT_READY",
        ready=True,
        posture="OBSERVE_ONLY",
    )
    drafts.append(bridge.subagent_ready(wake_id, readiness))
    return drafts, readiness


__all__ = ["run_subagent_wake"]
