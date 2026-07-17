"""Social content policy — internal operational text must never publish live."""

from __future__ import annotations

import re

INTERNAL_MARKERS: tuple[str, ...] = (
    "[advisory status — agent zero",
    "[advisory status - agent zero",
    "this is cargo/summary only",
    "no authority. operator disposes",
    "exciton phase",
    "bounded soak",
    "queue test",
    "status snapshot",
    "fixture-draft",
    "internal_only",
    "operator disposes",
    "confidence:",
    "topic:",
    "context:",
)

INTERNAL_TOPIC_BLOCKLIST: tuple[str, ...] = (
    "exciton phase 1",
    "bounded soak advisory",
    "queue test",
    "status snapshot",
    "soak status",
)


def is_internal_operational_content(body: str, *, topic: str = "") -> bool:
    low = body.lower().strip()
    if not low:
        return True
    if any(marker in low for marker in INTERNAL_MARKERS):
        return True
    topic_low = topic.lower().strip()
    if topic_low and any(t in topic_low for t in INTERNAL_TOPIC_BLOCKLIST):
        return True
    if re.match(r"^\[advisory status", low):
        return True
    return False


def publish_block_reason(body: str, *, topic: str = "", internal_only: bool = False) -> str | None:
    if internal_only:
        return "RED_INTERNAL_DRAFT_NOT_PUBLISHABLE"
    if is_internal_operational_content(body, topic=topic):
        return "RED_INTERNAL_OPERATIONS_CONTENT"
    return None


__all__ = ["INTERNAL_MARKERS", "INTERNAL_TOPIC_BLOCKLIST", "is_internal_operational_content", "publish_block_reason"]
