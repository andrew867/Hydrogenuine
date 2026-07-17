"""ELS readiness check runners — fail closed."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from hg_runtime.emergence.types import CheckStatus, ReadinessCheck, WakeProfile
from hg_runtime.replay import replay


@dataclass
class ReadinessContext:
    runtime_dir: Path
    bus: Any | None
    agent_id: str | None
    operator_id: str | None
    scope: tuple[str, ...]
    panic_active: bool
    lockdown_active: bool
    memory_available: bool
    oea_real: bool
    oea_available: bool
    live_cognition: bool
    live_provider_ok: bool
    secrets_redaction: bool
    stale_scratch: bool
    crr_recovery_marker: bool
    crr_snapshot_hash: str | None
    expected_world_state_hash: str | None
    replay_force_fail: bool = False
    clock_now: str = "1970-01-01T00:00:00.000000Z"

    def bus_head_seq(self) -> int | None:
        if self.bus is None:
            return None
        if hasattr(self.bus, "next_seq"):
            return max(0, int(self.bus.next_seq) - 1)
        return None


def _check_hash(check_id: str, status: str, reason: str | None) -> str:
    raw = f"{check_id}:{status}:{reason or ''}"
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _make_check(
    check_id: str,
    name: str,
    *,
    required: bool,
    status: CheckStatus,
    reason_code: str | None,
    evidence_ref: str | None,
    clock_now: str,
) -> ReadinessCheck:
    return ReadinessCheck(
        check_id=check_id,
        name=name,
        required_for_profile=required,
        status=status,
        reason_code=reason_code,
        evidence_ref=evidence_ref,
        started_at=clock_now,
        completed_at=clock_now,
        check_hash=_check_hash(check_id, status, reason_code),
    )


def run_check(check_id: str, profile: WakeProfile, ctx: ReadinessContext) -> ReadinessCheck:
    required = check_id in profile.required_checks
    name = check_id
    clock = ctx.clock_now

    if check_id == "config_valid":
        ok = ctx.runtime_dir is not None
        return _make_check(check_id, name, required=required, status="pass" if ok else "fail",
                           reason_code=None if ok else "CONFIG_INVALID", evidence_ref=str(ctx.runtime_dir), clock_now=clock)

    if check_id == "identity_bound":
        ok = bool(ctx.agent_id)
        return _make_check(check_id, name, required=required, status="pass" if ok else "fail",
                           reason_code=None if ok else "IDENTITY_MISSING", evidence_ref=ctx.agent_id, clock_now=clock)

    if check_id == "event_bus_available":
        ok = ctx.bus is not None
        return _make_check(check_id, name, required=required, status="pass" if ok else "fail",
                           reason_code=None if ok else "EVENT_BUS_MISSING", evidence_ref=None, clock_now=clock)

    if check_id == "event_log_accessible":
        log_dir = ctx.runtime_dir
        ok = log_dir.exists()
        return _make_check(check_id, name, required=required, status="pass" if ok else "fail",
                           reason_code=None if ok else "EVENT_LOG_INACCESSIBLE", evidence_ref=str(log_dir), clock_now=clock)

    if check_id == "event_head_read":
        head = ctx.bus_head_seq()
        ok = head is not None
        return _make_check(check_id, name, required=required, status="pass" if ok else "fail",
                           reason_code=None if ok else "EVENT_HEAD_UNREAD", evidence_ref=str(head), clock_now=clock)

    if check_id == "replay_verified_or_refused":
        if ctx.replay_force_fail:
            return _make_check(check_id, name, required=required, status="fail",
                               reason_code="REPLAY_MISMATCH", evidence_ref="forced", clock_now=clock)
        if ctx.bus is None:
            return _make_check(check_id, name, required=required, status="fail",
                               reason_code="REPLAY_SKIPPED_NO_BUS", evidence_ref=None, clock_now=clock)
        result = replay(ctx.runtime_dir)
        ok = result.ok
        return _make_check(check_id, name, required=required, status="pass" if ok else "fail",
                           reason_code=None if ok else "REPLAY_MISMATCH",
                           evidence_ref=result.state_hash, clock_now=clock)

    if check_id == "world_state_derived":
        if ctx.replay_force_fail:
            return _make_check(check_id, name, required=required, status="fail",
                               reason_code="WORLD_STATE_MISMATCH", evidence_ref=None, clock_now=clock)
        result = replay(ctx.runtime_dir)
        if not result.ok:
            return _make_check(check_id, name, required=required, status="fail",
                               reason_code="WORLD_STATE_DERIVATION_FAILED", evidence_ref=None, clock_now=clock)
        if ctx.expected_world_state_hash and result.state_hash != ctx.expected_world_state_hash:
            return _make_check(check_id, name, required=required, status="fail",
                               reason_code="WORLD_STATE_HASH_MISMATCH",
                               evidence_ref=result.state_hash, clock_now=clock)
        return _make_check(check_id, name, required=required, status="pass",
                           reason_code=None, evidence_ref=result.state_hash, clock_now=clock)

    if check_id == "memory_context_loaded_or_degraded":
        if ctx.memory_available:
            return _make_check(check_id, name, required=required, status="pass",
                               reason_code=None, evidence_ref="memory_ok", clock_now=clock)
        if profile.allow_degraded_memory:
            return _make_check(check_id, name, required=required, status="degraded",
                               reason_code="MEMORY_UNAVAILABLE_DEGRADED", evidence_ref=None, clock_now=clock)
        return _make_check(check_id, name, required=required, status="fail",
                           reason_code="MEMORY_REQUIRED", evidence_ref=None, clock_now=clock)

    if check_id == "aep_baseline_loaded":
        return _make_check(check_id, name, required=required, status="pass",
                           reason_code=None, evidence_ref="aep_baseline_stub", clock_now=clock)

    if check_id == "crr_status_loaded":
        if ctx.crr_recovery_marker and not ctx.crr_snapshot_hash:
            return _make_check(check_id, name, required=required, status="fail",
                               reason_code="CRR_SNAPSHOT_MISSING", evidence_ref=None, clock_now=clock)
        return _make_check(check_id, name, required=required, status="pass",
                           reason_code=None, evidence_ref=ctx.crr_snapshot_hash, clock_now=clock)

    if check_id == "oea_mode_known":
        mode = "real" if ctx.oea_real else "stub"
        if ctx.oea_real and not ctx.oea_available:
            return _make_check(check_id, name, required=required, status="degraded",
                               reason_code="OEA_REAL_UNAVAILABLE", evidence_ref=mode, clock_now=clock)
        return _make_check(check_id, name, required=required, status="pass",
                           reason_code=None, evidence_ref=mode, clock_now=clock)

    if check_id == "srp_mode_known":
        max_auto = os.environ.get("HG_SRP_MAX_AUTO_ENABLED", "0") == "1"
        return _make_check(check_id, name, required=required, status="pass",
                           reason_code=None, evidence_ref=f"max_auto={max_auto}", clock_now=clock)

    if check_id == "secrets_redaction_loaded":
        ok = ctx.secrets_redaction
        return _make_check(check_id, name, required=required, status="pass" if ok else "fail",
                           reason_code=None if ok else "SECRETS_REDACTION_MISSING", evidence_ref=None, clock_now=clock)

    if check_id == "capability_catalog_loaded_if_needed":
        return _make_check(check_id, name, required=required, status="pass",
                           reason_code=None, evidence_ref="catalog_metadata_only", clock_now=clock)

    if check_id == "live_provider_validated_if_needed":
        if not profile.require_live_provider:
            return _make_check(check_id, name, required=required, status="not_applicable",
                               reason_code=None, evidence_ref=None, clock_now=clock)
        ok = ctx.live_cognition and ctx.live_provider_ok
        return _make_check(check_id, name, required=required, status="pass" if ok else "fail",
                           reason_code=None if ok else "LIVE_PROVIDER_MISSING", evidence_ref=None, clock_now=clock)

    if check_id == "singleton_lease_acquired_if_needed":
        return _make_check(check_id, name, required=required, status="skipped",
                           reason_code="SINGLETON_NOT_IMPLEMENTED", evidence_ref=None, clock_now=clock)

    if check_id == "no_pending_panic":
        ok = not ctx.panic_active
        return _make_check(check_id, name, required=required, status="pass" if ok else "fail",
                           reason_code=None if ok else "PANIC_ACTIVE", evidence_ref=None, clock_now=clock)

    if check_id == "no_lockdown_without_operator_ack":
        if ctx.lockdown_active:
            return _make_check(check_id, name, required=required, status="fail",
                               reason_code="LOCKDOWN_WITHOUT_ACK", evidence_ref=None, clock_now=clock)
        return _make_check(check_id, name, required=required, status="pass",
                           reason_code=None, evidence_ref=None, clock_now=clock)

    return _make_check(check_id, name, required=required, status="fail",
                       reason_code="UNKNOWN_CHECK", evidence_ref=None, clock_now=clock)


def run_all_checks(profile: WakeProfile, ctx: ReadinessContext) -> list[ReadinessCheck]:
    checks: list[ReadinessCheck] = []
    for check_id in profile.required_checks:
        checks.append(run_check(check_id, profile, ctx))
    if profile.require_scope and not ctx.scope:
        checks.append(
            _make_check(
                "subagent_scope_bound",
                "subagent_scope_bound",
                required=True,
                status="fail",
                reason_code="SCOPE_MISSING",
                evidence_ref=None,
                clock_now=ctx.clock_now,
            )
        )
    elif profile.require_scope:
        checks.append(
            _make_check(
                "subagent_scope_bound",
                "subagent_scope_bound",
                required=True,
                status="pass",
                reason_code=None,
                evidence_ref=",".join(ctx.scope),
                clock_now=ctx.clock_now,
            )
        )
    return checks


def aggregate_verdict(
    checks: list[ReadinessCheck],
    *,
    profile: WakeProfile,
    panic_active: bool,
    lockdown_active: bool,
    replay_failed: bool,
    refuse_on_replay_mismatch: bool,
) -> tuple[str, str | None]:
    """Return (verdict, refusal_reason)."""
    if panic_active:
        return "safe_mode", "PANIC_ACTIVE"
    if lockdown_active:
        return "refused", "LOCKDOWN_ACTIVE"
    if replay_failed and refuse_on_replay_mismatch:
        return "safe_mode", "REPLAY_MISMATCH"

    failed_required = [
        c for c in checks if c.required_for_profile and c.status == "fail"
    ]
    if failed_required:
        return "refused", failed_required[0].reason_code or "CHECK_FAILED"

    degraded = [c for c in checks if c.status == "degraded"]
    if degraded and profile.allow_degraded_ready:
        return "degraded_ready", None
    if degraded and not profile.allow_degraded_ready:
        return "refused", degraded[0].reason_code or "DEGRADED_NOT_ALLOWED"

    return "ready", None


__all__ = [
    "ReadinessContext",
    "aggregate_verdict",
    "run_all_checks",
    "run_check",
]
