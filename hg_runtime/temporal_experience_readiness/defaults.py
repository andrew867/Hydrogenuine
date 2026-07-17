"""Default safety matrix for first-wake profile."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hg_runtime.temporal_experience_readiness.schema import DefaultSafetyMatrix

WORKSPACE = Path(__file__).resolve().parents[2]
FIRST_WAKE_PROFILE = WORKSPACE / "configs/runtime/agent-zero-first-wake-local-openvino.json"

SAFE_ON = [
    "wake_refresh", "chrono", "chrono_lock", "will", "trust_boundary", "self_mirror",
    "anchor_status_if_handoff", "ewj_status", "storage_proof_reads", "capability_discovery",
    "organ_status", "local_openvino", "audio_status", "tts_to_file_status", "safe_local_tools",
    "denial_tests",
]

DANGEROUS_OFF = [
    "live_social_publish", "live_email_send", "account_creation", "live_playback", "live_mic",
    "live_browser", "cloud_providers", "live_oea", "live_ter", "srp_apply", "privileged_shell",
    "autonomous_github_push",
]


def audit_profile_defaults(profile: dict[str, Any] | None = None) -> DefaultSafetyMatrix:
    if profile is None and FIRST_WAKE_PROFILE.exists():
        profile = json.loads(FIRST_WAKE_PROFILE.read_text(encoding="utf-8"))
    profile = profile or {}
    violations: list[str] = []
    if profile.get("publish"):
        violations.append("RED_LIVE_SIDE_EFFECT: publish enabled")
    if profile.get("live_oea"):
        violations.append("RED_LIVE_SIDE_EFFECT: live_oea enabled")
    if profile.get("live_ter"):
        violations.append("RED_LIVE_SIDE_EFFECT: live_ter enabled")
    if profile.get("srp_apply"):
        violations.append("RED_LIVE_SIDE_EFFECT: srp_apply enabled")
    if profile.get("cloud_providers_enabled") and profile.get("external_network_allowed"):
        violations.append("cloud+network enabled without explicit operator flag")
    if profile.get("permission_granted"):
        violations.append("RED_AUTHORITY_CONVERSION: permission_granted true")
    if profile.get("authority_created"):
        violations.append("RED_AUTHORITY_CONVERSION: authority_created true")
    return DefaultSafetyMatrix(
        safe_defaults_on=SAFE_ON,
        dangerous_defaults_off=DANGEROUS_OFF,
        violations=violations,
        ok=not any(v.startswith("RED_") for v in violations),
    )


__all__ = ["audit_profile_defaults", "FIRST_WAKE_PROFILE"]
