"""Envelope validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from hg_runtime.real_soak_launch.moltbook_envelope import MoltbookLiveEnvelope
from hg_runtime.real_soak_launch.schema import RealSoakLaunchVerdict, load_launch_policy, new_id, now_iso


@dataclass
class EnvelopeValidationDecision:
    decision_id: str
    valid: bool
    verdict: str
    issues: tuple[str, ...]
    created_at: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "valid": self.valid,
            "verdict": self.verdict,
            "issues": list(self.issues),
            "created_at": self.created_at,
        }


def validate_moltbook_envelope(envelope: MoltbookLiveEnvelope) -> EnvelopeValidationDecision:
    policy = load_launch_policy()
    issues: list[str] = []

    if envelope.platform != "moltbook":
        issues.append(RealSoakLaunchVerdict.RED_CHANGE_PLATFORM.value)
    if envelope.allowed_action_type != "publish_post":
        issues.append("RED_ENVELOPE_ALLOWS_ACTION_TYPE_EXPANSION")
    if envelope.max_live_posts < 0:
        issues.append(RealSoakLaunchVerdict.RED_UNBOUNDED_POSTS.value)
    if policy.get("max_live_posts_must_be_finite") and envelope.max_live_posts > 100:
        issues.append(RealSoakLaunchVerdict.RED_UNBOUNDED_POSTS.value)
    if not envelope.valid_until:
        issues.append(RealSoakLaunchVerdict.RED_UNBOUNDED_TIME.value)
    else:
        try:
            until = datetime.fromisoformat(envelope.valid_until.replace("Z", "+00:00"))
            if until <= datetime.now(timezone.utc):
                issues.append("envelope_expired")
        except (ValueError, TypeError):
            issues.append(RealSoakLaunchVerdict.RED_UNBOUNDED_TIME.value)
    if envelope.max_posts_per_hour < 0 or envelope.max_posts_per_hour > 10:
        issues.append(RealSoakLaunchVerdict.RED_UNBOUNDED_POSTS.value)

    valid = not any(i.startswith("RED_") for i in issues)
    verdict = "GREEN_ENVELOPE_VALID" if valid else issues[0]
    if envelope.max_live_posts == 0:
        verdict = RealSoakLaunchVerdict.YELLOW_QUOTA_ZERO.value if valid else verdict

    return EnvelopeValidationDecision(
        decision_id=new_id("env-val"),
        valid=valid,
        verdict=verdict,
        issues=tuple(issues),
        created_at=now_iso(),
    )
