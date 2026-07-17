"""Freshness evaluation for live read items."""

from __future__ import annotations

from datetime import datetime, timezone

from hg_runtime.live_read_endurance.schema import LiveReadFreshnessStatus, load_policy, new_id, now_iso
from hg_runtime.social_capability.read_receipts import LiveReadVerdict


def assess_freshness(
    *,
    read_verdict: LiveReadVerdict,
    item_count: int,
    read_completed_at: str,
    max_stale_seconds: int | None = None,
) -> tuple[LiveReadFreshnessStatus, str]:
    policy = load_policy()
    stale_limit = max_stale_seconds or int(policy.get("max_stale_seconds", 900))

    if read_verdict == LiveReadVerdict.YELLOW_CREDENTIALS_MISSING:
        return LiveReadFreshnessStatus.CREDENTIALS_MISSING, new_id("fresh")
    if read_verdict == LiveReadVerdict.YELLOW_LIVE_READ_DISABLED:
        return LiveReadFreshnessStatus.UNAVAILABLE, new_id("fresh")
    if read_verdict == LiveReadVerdict.RED_FIXTURE_FEED_USED_IN_RUNTIME:
        return LiveReadFreshnessStatus.FIXTURE, new_id("fresh")
    if read_verdict in (LiveReadVerdict.YELLOW_LIVE_API_UNREACHABLE, LiveReadVerdict.YELLOW_CREDENTIALS_INVALID):
        return LiveReadFreshnessStatus.UNAVAILABLE, new_id("fresh")

    try:
        ts = datetime.fromisoformat(read_completed_at.replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - ts).total_seconds()
        if age > stale_limit:
            return LiveReadFreshnessStatus.STALE, new_id("fresh")
    except ValueError:
        return LiveReadFreshnessStatus.INVALID, new_id("fresh")

    if item_count == 0 and read_verdict == LiveReadVerdict.YELLOW_NO_ITEMS_RETURNED:
        if policy.get("empty_feed_green_requires_freshness_proof", True):
            return LiveReadFreshnessStatus.EMPTY_BUT_FRESH, new_id("fresh")
        return LiveReadFreshnessStatus.UNAVAILABLE, new_id("fresh")

    if read_verdict == LiveReadVerdict.GREEN_LIVE_READ_OK:
        return LiveReadFreshnessStatus.FRESH, new_id("fresh")

    return LiveReadFreshnessStatus.UNAVAILABLE, new_id("fresh")
