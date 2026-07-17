"""SQP-5 review policy adapter.

Converts SQP metadata (quality scores, provenance, staleness/conflict) plus AIS
signals (fever, quarantine, security findings) and the ORP review decision ledger
into *non-authoritative* review policy hints.

Doctrine:

* A review hint is not operator approval.
* A review hint is not promotion, not action, not truth.
* A review hint cannot override an AIS fever restriction.
* A review hint cannot override a quarantine.
* A review hint cannot authorize tools or delete anything.

The adapter respects AIS restrictions: a permissive hint
(``ALLOW_PROVISIONAL_REVIEW``) is *blocked* and downgraded to a restrictive hint
whenever the source is under a fever restriction or is quarantined. Fever
restricts, never unlocks.
"""

from __future__ import annotations

from hg_runtime.agent_immune_system.restriction_policy import restrictions_for_level, unlock_actions_for_level
from hg_runtime.source_quality_provenance.hashing import record_hash
from hg_runtime.source_quality_provenance.review_hint_builder import build_blocked_review_hint, build_review_hint
from hg_runtime.source_quality_provenance.review_priority import build_review_priority_record, priority_for_hint
from hg_runtime.source_quality_provenance.schemas import (
    REVIEW_HINT_TYPES,
    REVIEW_PRIORITY_BANDS,
    assert_neutral,
    neutral_flags,
)

_RESTRICTIVE_FEVER_LEVELS = {"RED_FEVER", "PANIC_FEVER"}


def classify_hint(signals: dict) -> str:
    if signals.get("security_finding"):
        return "BLOCK_PROMOTION_REQUEST"
    if signals.get("retraction_conflict"):
        return "RETRACTION_RECOMMENDED"
    if signals.get("quarantined"):
        return "QUARANTINE_RECOMMENDED"
    if signals.get("stale_by_policy"):
        return "REQUIRE_OPERATOR_CONFIRMATION"
    if signals.get("conflict"):
        return "PRIORITIZE_REVIEW"
    if signals.get("single_source"):
        return "REQUIRE_SECOND_SOURCE"
    if signals.get("low_quality"):
        return "REQUEST_MORE_EVIDENCE"
    return "ALLOW_PROVISIONAL_REVIEW"


def _is_restricted(signals: dict) -> tuple[bool, str]:
    fever_level = signals.get("fever_level", "NORMAL")
    if signals.get("quarantined"):
        return True, "quarantine_active"
    if fever_level in _RESTRICTIVE_FEVER_LEVELS:
        return True, f"fever_restriction:{fever_level}"
    return False, ""


def build_sqp5_inputs() -> dict:
    """Deterministic fixtures exercising every hint type, priority band, and a block."""
    return {
        "sources": [
            {"source_id": "sqp5-source-clean", "fever_level": "NORMAL"},
            {"source_id": "sqp5-source-thin", "low_quality": True, "fever_level": "NORMAL"},
            {"source_id": "sqp5-source-single", "single_source": True, "fever_level": "NORMAL"},
            {"source_id": "sqp5-source-conflict", "conflict": True, "fever_level": "WATCH"},
            {"source_id": "sqp5-source-stale", "stale_by_policy": True, "fever_level": "NORMAL"},
            {"source_id": "sqp5-source-quarantine", "quarantined": True, "fever_level": "YELLOW_FEVER"},
            {"source_id": "sqp5-source-retract", "retraction_conflict": True, "fever_level": "RED_FEVER"},
            {"source_id": "sqp5-source-security", "security_finding": True, "fever_level": "RED_FEVER"},
            # Otherwise-clean source under RED fever -> permissive hint is blocked.
            {"source_id": "sqp5-source-fevered", "fever_level": "RED_FEVER"},
        ],
        "review_ledger_ref": "docs/proofs/autonomous_agent_zero/ORP-1-OPERATOR-REVIEW-DECISION-LEDGER",
    }


def build_review_policy_adapter_layer(inputs: dict) -> dict:
    hints: list[dict] = []
    priorities: list[dict] = []
    blocked: list[dict] = []

    for src in inputs["sources"]:
        sid = src["source_id"]
        computed = classify_hint(src)
        restricted, reason = _is_restricted(src)
        emitted = computed

        # A permissive hint can never escape a fever/quarantine restriction.
        if restricted and computed == "ALLOW_PROVISIONAL_REVIEW":
            emitted = "REQUIRE_OPERATOR_CONFIRMATION"
            blocked.append(
                build_blocked_review_hint(
                    hint_id=f"sqp5-blocked-{sid}",
                    source_id=sid,
                    requested_hint_type=computed,
                    replacement_hint_type=emitted,
                    block_reason=reason,
                )
            )

        priority = priority_for_hint(emitted)
        rationale = [f"signals={sorted(k for k, v in src.items() if v is True)}", f"fever_level={src.get('fever_level', 'NORMAL')}"]
        if restricted:
            rationale.append(f"restriction_respected:{reason}")
        hints.append(
            build_review_hint(
                hint_id=f"sqp5-hint-{sid}", source_id=sid, hint_type=emitted, priority=priority, rationale=rationale
            )
        )
        priorities.append(build_review_priority_record(source_id=sid, hint_type=emitted, priority=priority))

    manifest = build_review_policy_adapter_manifest(hints, priorities, blocked)
    return {"hints": hints, "priorities": priorities, "blocked_hints": blocked, "manifest": manifest}


def build_review_policy_adapter_manifest(hints: list[dict], priorities: list[dict], blocked: list[dict]) -> dict:
    hint_types = sorted({h["hint_type"] for h in hints})
    # Requested types include blocked (pre-downgrade) permissive hints.
    requested_types = sorted(set(hint_types) | {b["requested_hint_type"] for b in blocked})
    priority_bands = sorted({p["priority"] for p in priorities})
    # Demonstrate fever restricts but never unlocks (AIS-INV-02).
    fever_unlock_actions = unlock_actions_for_level("RED_FEVER")
    manifest = {
        "schema_version": "1",
        "record_type": "review_policy_adapter_manifest_v1",
        "phase": "SQP-5",
        "hint_count": len(hints),
        "priority_record_count": len(priorities),
        "blocked_hint_count": len(blocked),
        "hint_types_present": hint_types,
        "hint_types_including_blocked": requested_types,
        "priority_bands_present": priority_bands,
        "all_hint_types_present": set(requested_types) >= REVIEW_HINT_TYPES,
        "all_priority_bands_present": set(priority_bands) >= REVIEW_PRIORITY_BANDS,
        "red_fever_restrictions": restrictions_for_level("RED_FEVER"),
        "fever_unlock_actions": fever_unlock_actions,
        "fever_never_unlocks": fever_unlock_actions == [],
        "doctrine_note": "Review hints are advisory; fever restricts and never unlocks; quarantine is respected.",
        "review_hint_treated_as_operator_approval": False,
        "hint_overrides_fever_restriction": False,
        "hint_overrides_quarantine": False,
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)
    assert_neutral(manifest)
    return manifest
