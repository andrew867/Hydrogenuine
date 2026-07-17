"""Built-in ELS wake profiles."""

from __future__ import annotations

from hg_runtime.emergence.types import WakeProfile

_COMMON_AGENT0 = (
    "config_valid",
    "identity_bound",
    "event_bus_available",
    "event_log_accessible",
    "event_head_read",
    "replay_verified_or_refused",
    "world_state_derived",
    "memory_context_loaded_or_degraded",
    "aep_baseline_loaded",
    "crr_status_loaded",
    "oea_mode_known",
    "srp_mode_known",
    "no_pending_panic",
)

_PROFILES: dict[str, WakeProfile] = {
    "agent0_full": WakeProfile(
        profile_id="agent0_full",
        required_checks=_COMMON_AGENT0,
        allow_degraded_memory=True,
        allow_quiet_settling=True,
        require_secrets_redaction=False,
    ),
    "worker_subagent": WakeProfile(
        profile_id="worker_subagent",
        required_checks=(
            "config_valid",
            "identity_bound",
            "event_bus_available",
            "event_head_read",
            "world_state_derived",
            "no_pending_panic",
        ),
        require_scope=False,
        is_subagent=True,
    ),
    "task_subagent": WakeProfile(
        profile_id="task_subagent",
        required_checks=(
            "config_valid",
            "identity_bound",
            "event_bus_available",
            "event_head_read",
            "world_state_derived",
            "capability_catalog_loaded_if_needed",
            "no_pending_panic",
        ),
        require_scope=True,
        is_subagent=True,
    ),
    "maintenance_subagent": WakeProfile(
        profile_id="maintenance_subagent",
        required_checks=(
            "config_valid",
            "identity_bound",
            "event_bus_available",
            "srp_mode_known",
            "no_pending_panic",
        ),
        require_scope=True,
        is_subagent=True,
    ),
    "oea_capability_worker": WakeProfile(
        profile_id="oea_capability_worker",
        required_checks=(
            "config_valid",
            "identity_bound",
            "oea_mode_known",
            "capability_catalog_loaded_if_needed",
            "no_pending_panic",
        ),
        require_scope=True,
        is_subagent=True,
    ),
    "live_cognition_worker": WakeProfile(
        profile_id="live_cognition_worker",
        required_checks=(
            "config_valid",
            "identity_bound",
            "live_provider_validated_if_needed",
            "no_pending_panic",
        ),
        require_live_provider=True,
        require_scope=True,
        is_subagent=True,
    ),
    "plt_operator_surface": WakeProfile(
        profile_id="plt_operator_surface",
        required_checks=(
            "config_valid",
            "secrets_redaction_loaded",
            "event_bus_available",
            "no_pending_panic",
        ),
        require_secrets_redaction=True,
    ),
    "dep_appliance": WakeProfile(
        profile_id="dep_appliance",
        required_checks=(
            "config_valid",
            "event_log_accessible",
            "replay_verified_or_refused",
            "oea_mode_known",
            "srp_mode_known",
            "singleton_lease_acquired_if_needed",
            "no_pending_panic",
        ),
        allow_degraded_memory=True,
    ),
    "crr_reentry": WakeProfile(
        profile_id="crr_reentry",
        required_checks=(
            "config_valid",
            "identity_bound",
            "event_bus_available",
            "event_head_read",
            "replay_verified_or_refused",
            "world_state_derived",
            "crr_status_loaded",
            "no_pending_panic",
        ),
        allow_degraded_memory=True,
    ),
}


def get_profile(profile_id: str) -> WakeProfile:
    key = profile_id.strip().lower()
    if key not in _PROFILES:
        raise KeyError(f"unknown wake profile: {profile_id!r}")
    return _PROFILES[key]


def list_profiles() -> tuple[str, ...]:
    return tuple(sorted(_PROFILES.keys()))


__all__ = ["get_profile", "list_profiles"]
