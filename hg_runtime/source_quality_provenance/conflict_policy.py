"""SQP-4 staleness and conflict policy (non-authoritative).

This policy declares, in data, that staleness and conflict detection are
descriptive metadata only. Staleness is never falsity; conflict never resolves
truth and never deletes a source. At most, these signals may produce a review
hint for a human operator.
"""

from __future__ import annotations

CONFLICT_POLICY = {
    "policy_id": "sqp4-staleness-conflict-policy-v1",
    "stale_is_false": False,
    "conflict_resolves_truth": False,
    "conflict_is_deletion": False,
    "conflict_authorizes_action": False,
    "conflict_authorizes_tools": False,
    "staleness_may_emit_review_hint_only": True,
    "contradiction_remains_visible": True,
    "source_preserved": True,
    "doctrine_note": "Stale source is not false. Conflict is not truth resolution.",
}

# Deterministic policy thresholds expressed as opaque age classes, not live dates.
STALENESS_AGE_CLASSES = ("CURRENT", "OLD", "STALE")
