"""Live post guard — sits before any live Moltbook dispatch."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from hg_runtime.real_soak_launch.moltbook_envelope import MoltbookLiveEnvelope
from hg_runtime.real_soak_launch.schema import RealSoakLaunchVerdict, load_launch_policy, new_id, now_iso


@dataclass
class LivePostGuardDecision:
    decision_id: str
    allowed: bool
    verdict: str
    refusal_reasons: tuple[str, ...]
    dry_run_only: bool
    created_at: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "allowed": self.allowed,
            "verdict": self.verdict,
            "refusal_reasons": list(self.refusal_reasons),
            "dry_run_only": self.dry_run_only,
            "created_at": self.created_at,
        }


FORBIDDEN_ACTIONS = frozenset(
    {"reply", "comment", "send", "mass_message", "browser", "hardware", "publish_reply", "publish_comment"}
)


def evaluate_live_post_guard(
    *,
    envelope: MoltbookLiveEnvelope | None,
    action_type: str = "publish_post",
    platform: str = "moltbook",
    community_or_route: str = "general",
    candidate_receipt_ref: str | None = None,
    permit_receipt_ref: str | None = None,
    content_hash: str | None = None,
    stop_active: bool = False,
    panic_active: bool = False,
    live_posts_used: int = 0,
    posts_this_hour: int = 0,
    dry_run: bool = False,
    require_receipts: bool = True,
) -> LivePostGuardDecision:
    policy = load_launch_policy()
    reasons: list[str] = []

    if action_type in FORBIDDEN_ACTIONS or action_type != "publish_post":
        reasons.append(RealSoakLaunchVerdict.RED_FORBIDDEN_ACTION.value)
    if platform != "moltbook":
        reasons.append(RealSoakLaunchVerdict.RED_CHANGE_PLATFORM.value)
    if community_or_route != (envelope.allowed_community_or_route if envelope else community_or_route):
        if envelope and community_or_route != envelope.allowed_community_or_route:
            reasons.append(RealSoakLaunchVerdict.RED_CHANGE_COMMUNITY.value)

    if dry_run:
        return LivePostGuardDecision(
            decision_id=new_id("live-guard"),
            allowed=False,
            verdict="GREEN_DRY_RUN_ONLY",
            refusal_reasons=(),
            dry_run_only=True,
            created_at=now_iso(),
        )

    live_env = (
        os.environ.get("HG_SOCIAL_LIVE_PUBLISH", "false").lower() == "true"
        or os.environ.get("HG_ENABLE_LIVE_SOCIAL_WRITES", "false").lower() == "true"
    )
    if not live_env:
        reasons.append(RealSoakLaunchVerdict.YELLOW_ENVELOPE_NOT_ARMED.value)

    if envelope is None:
        reasons.append(RealSoakLaunchVerdict.RED_NO_ENVELOPE.value)
    elif not envelope.is_armed():
        reasons.append(RealSoakLaunchVerdict.YELLOW_ENVELOPE_NOT_ARMED.value)
    elif envelope.is_expired():
        reasons.append("envelope_expired")
    elif envelope.max_live_posts <= 0:
        reasons.append(RealSoakLaunchVerdict.YELLOW_QUOTA_ZERO.value)
    elif live_posts_used >= envelope.max_live_posts:
        reasons.append(RealSoakLaunchVerdict.RED_INCREASE_QUOTA.value)
    elif posts_this_hour >= envelope.max_posts_per_hour:
        reasons.append(RealSoakLaunchVerdict.RED_UNBOUNDED_POSTS.value)

    if policy.get("stop_panic_blocks_live_post"):
        if stop_active:
            reasons.append(RealSoakLaunchVerdict.RED_STOP.value)
        if panic_active:
            reasons.append(RealSoakLaunchVerdict.RED_PANIC.value)

    if require_receipts and policy.get("candidate_receipt_required") and not candidate_receipt_ref:
        reasons.append(RealSoakLaunchVerdict.RED_NO_CANDIDATE.value)
    if require_receipts and policy.get("permit_receipt_required") and not permit_receipt_ref:
        reasons.append(RealSoakLaunchVerdict.RED_NO_PERMIT.value)
    if require_receipts and policy.get("content_hash_required") and not content_hash:
        reasons.append("content_hash_missing")

    if os.environ.get("HG_LIVE_BROWSER_ENABLED", "false").lower() == "true":
        reasons.append(RealSoakLaunchVerdict.RED_FORBIDDEN_ACTION.value)

    allowed = len(reasons) == 0
    verdict = "GREEN_LIVE_POST_ALLOWED" if allowed else reasons[0]
    return LivePostGuardDecision(
        decision_id=new_id("live-guard"),
        allowed=allowed,
        verdict=verdict,
        refusal_reasons=tuple(reasons),
        dry_run_only=False,
        created_at=now_iso(),
    )
