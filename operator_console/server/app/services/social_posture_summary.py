from __future__ import annotations

from typing import Any


def build_social_posture_summary(
    *,
    agency_control_summary: dict[str, Any] | None,
    self_model_summary: dict[str, Any] | None,
    relationship_memory_summary: dict[str, Any] | None,
    assigned_social_accounts: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    agency_control_summary = agency_control_summary if isinstance(agency_control_summary, dict) else {}
    self_model_summary = self_model_summary if isinstance(self_model_summary, dict) else {}
    relationship_memory_summary = relationship_memory_summary if isinstance(relationship_memory_summary, dict) else {}
    assigned_social_accounts = assigned_social_accounts if isinstance(assigned_social_accounts, list) else []

    effective_mode = str(agency_control_summary.get("effective_mode") or agency_control_summary.get("mode") or "normal").strip() or "normal"
    outbound_lane_policy = str(agency_control_summary.get("outbound_lane_policy") or "unrestricted").strip() or "unrestricted"
    engagement_mode = str(self_model_summary.get("dominant_engagement_mode") or "").strip() or None
    relationship_signal = str(self_model_summary.get("relationship_signal") or "").strip() or None
    dominant_relationship_type = str(relationship_memory_summary.get("dominant_relationship_type") or "").strip() or None

    active_platforms = sorted(
        {
            str(account.get("platform") or "").strip()
            for account in assigned_social_accounts
            if str(account.get("platform") or "").strip()
        }
    )
    healthy_accounts = sum(
        1
        for account in assigned_social_accounts
        if str(((account.get("continuity_summary") or {}).get("status") or "")).strip().lower() == "healthy"
    )
    ready_accounts = sum(1 for account in assigned_social_accounts if bool((account.get("readiness_summary") or {}).get("ready")))

    posture = "mixed"
    if effective_mode == "held" or outbound_lane_policy == "blocked":
        posture = "paused"
    elif effective_mode == "review_only":
        posture = "supervised"
    elif outbound_lane_policy == "drafts_only":
        posture = "drafting"
    elif outbound_lane_policy == "replies_only":
        posture = "conversational"
    elif engagement_mode == "direct":
        posture = "broadcast"
    elif engagement_mode == "reciprocal":
        posture = "conversational"

    reply_bias = "balanced"
    if outbound_lane_policy == "replies_only":
        reply_bias = "reply_heavy"
    elif engagement_mode == "direct":
        reply_bias = "broadcast_heavy"
    elif engagement_mode == "reciprocal":
        reply_bias = "reply_heavy"

    relationship_orientation = relationship_signal or dominant_relationship_type or None

    status = "partial"
    if effective_mode == "held" or outbound_lane_policy == "blocked":
        status = "restricted"
    elif active_platforms and ready_accounts and healthy_accounts:
        status = "healthy"
    elif active_platforms:
        status = "partial"
    else:
        status = "missing"

    return {
        "status": status,
        "posture": posture,
        "effective_mode": effective_mode,
        "outbound_lane_policy": outbound_lane_policy,
        "engagement_mode": engagement_mode,
        "reply_bias": reply_bias,
        "relationship_orientation": relationship_orientation,
        "active_platforms": active_platforms,
        "active_platform_count": len(active_platforms),
        "ready_account_count": ready_accounts,
        "healthy_account_count": healthy_accounts,
        "restricted": status == "restricted",
    }
