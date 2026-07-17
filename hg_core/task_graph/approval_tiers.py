"""
Approval tiers (S3): Tier 0 (no approval), Tier 1 (approval required), Tier 2 (always manual).

get_approval_tier(action_type, destination) -> 0 | 1 | 2.
format_approval_request(...) -> dict for logging/API.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# High-risk destinations or actions that require Tier 1 or 2
HIGH_RISK_DESTINATIONS = frozenset({"external_api", "payment", "admin"})
TIER_1_DESTINATIONS = frozenset({"twitter", "mastodon", "bluesky"})  # sensitive social
TIER_2_ACTIONS = frozenset({"delete_user_data", "apply_entity_dag"})


def get_approval_tier(
    action_type: str,
    destination: Optional[str] = None,
) -> int:
    """
    Return approval tier for (action_type, destination): 0 (none), 1 (required), 2 (always manual).
    """
    if action_type in TIER_2_ACTIONS or (destination and destination in HIGH_RISK_DESTINATIONS):
        return 2
    if destination and destination in TIER_1_DESTINATIONS:
        return 1
    return 0


def format_approval_request(
    action_type: str,
    destination: Optional[str],
    content_summary: str,
    evidence_pointer: Optional[str] = None,
) -> Dict[str, Any]:
    """Build approval request artifact for logging/API."""
    tier = get_approval_tier(action_type, destination)
    return {
        "action_type": action_type,
        "destination": destination,
        "approval_tier": tier,
        "content_summary": content_summary[:500] if content_summary else "",
        "evidence_pointer": evidence_pointer,
        "on_approve": "execute action",
        "on_deny": "skip action and record denied",
    }
