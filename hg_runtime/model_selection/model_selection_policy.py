"""Model selection policy.

Picks a model for a given call intent from available roster.
Selection prefers healthy models and factors in failed attempts.
No hard allowlist. No model authority. No consensus as proof.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from hg_runtime.model_selection.model_roster import ModelRoster
from hg_runtime.model_selection.model_classifier import ModelClassification
from hg_runtime.model_selection.model_rotation import (
    ModelRotationTracker,
    HEALTH_QUARANTINED, HEALTH_FORBIDDEN, HEALTH_COOLDOWN,
)

CALL_INTENTS = (
    "source_summary", "skeptical_review", "formalism_audit",
    "synthesis", "public_safe_summary", "backlog_mini_summary",
    "backlog_gap_scan", "deep_witness",
)

INTENT_ROLE_MAP = {
    "source_summary": ["fast_triage", "instruction_following"],
    "skeptical_review": ["skeptical_review", "instruction_following"],
    "formalism_audit": ["formalism_audit", "coding"],
    "synthesis": ["instruction_following", "deeper_witness"],
    "public_safe_summary": ["fast_triage", "instruction_following"],
    "backlog_mini_summary": ["backlog_triage", "fast_triage"],
    "backlog_gap_scan": ["fast_triage", "instruction_following"],
    "deep_witness": ["deeper_witness", "skeptical_review"],
}


@dataclass
class SelectionResult:
    model_id: str
    reason: str
    variation_reason: str = ""
    timeout_cooldown_applied: bool = False
    resource_risk: str = "unknown"

    def to_dict(self) -> dict:
        return {
            "selected_model_id": self.model_id,
            "selection_reason": self.reason,
            "variation_reason": self.variation_reason,
            "timeout_cooldown_applied": self.timeout_cooldown_applied,
            "resource_risk": self.resource_risk,
            "model_selection_is_not_authority": True,
            "model_output_is_not_truth": True,
            "consensus_is_not_proof": True,
            "promotion_allowed": False,
            "operator_review_required": True,
        }


def _sort_key(m: ModelClassification, usage: dict, attempts: dict) -> tuple:
    """Sort models: fewest attempts first, then fewest successes, for balanced rotation."""
    return (attempts.get(m.model_id, 0), usage.get(m.model_id, 0))


def select_model(
    roster: ModelRoster,
    call_intent: str,
    *,
    usage_counts: dict[str, int] | None = None,
    timeout_cooldown: set[str] | None = None,
    is_required: bool = True,
    prefer_variation: bool = False,
    rotation_tracker: ModelRotationTracker | None = None,
    exclude_models: set[str] | None = None,
) -> SelectionResult | None:
    usage = usage_counts or {}
    cooled = timeout_cooldown or set()
    excluded = exclude_models or set()

    preferred_roles = INTENT_ROLE_MAP.get(call_intent, [])
    candidates = roster.within_risk_ceiling()
    candidates = [m for m in candidates if not m.is_embedding]

    if not candidates:
        return None

    # Remove explicitly excluded models
    if excluded:
        filtered = [m for m in candidates if m.model_id not in excluded]
        if filtered:
            candidates = filtered

    # Remove quarantined and forbidden models
    if rotation_tracker:
        filtered = [m for m in candidates
                    if rotation_tracker.is_selectable(m.model_id)]
        if filtered:
            candidates = filtered

    # Remove cooled-down models (both tracker-level and legacy cooldown set)
    if rotation_tracker:
        cooled_out = [m for m in candidates
                      if rotation_tracker.model_health(m.model_id) != HEALTH_COOLDOWN]
        if cooled_out:
            candidates = cooled_out
    if cooled:
        filtered = [m for m in candidates if m.model_id not in cooled]
        if filtered:
            candidates = filtered

    # Prefer models matching the call intent's role
    role_matched = []
    for role in preferred_roles:
        role_matched = [m for m in candidates if role in m.role_hints]
        if role_matched:
            break
    if role_matched:
        candidates = role_matched

    # Prefer operator-preferred models
    preferred = [m for m in candidates if m.model_id in roster.prefer_models]
    if preferred:
        candidates = preferred

    # Prefer models with recent substantive success
    if rotation_tracker:
        proven = [m for m in candidates
                  if rotation_tracker.has_recent_success(m.model_id)]
        if proven and len(proven) < len(candidates):
            unproven = [m for m in candidates if m not in proven]
            # Only prefer proven if unproven have no attempts yet (cold start)
            # or unproven have all failed
            all_unproven_failed = all(
                rotation_tracker.attempt_count(m.model_id) > 0
                and not rotation_tracker.has_recent_success(m.model_id)
                for m in unproven
            )
            if all_unproven_failed:
                candidates = proven

    # Sort by balanced rotation: attempts count, not just successes
    attempts = {}
    if rotation_tracker:
        attempts = {m.model_id: rotation_tracker.attempt_count(m.model_id)
                    for m in candidates}
    candidates.sort(key=lambda m: _sort_key(m, usage, attempts))

    selected = candidates[0]
    reason = f"selected for {call_intent}"
    variation_reason = ""

    if prefer_variation and len(candidates) > 1:
        if usage.get(selected.model_id, 0) == 0:
            variation_reason = "least_used"
        else:
            variation_reason = "least_used_among_candidates"
    elif len(candidates) == 1:
        variation_reason = "only_one_candidate"

    cooldown_applied = selected.model_id in cooled and is_required

    return SelectionResult(
        model_id=selected.model_id,
        reason=reason,
        variation_reason=variation_reason,
        timeout_cooldown_applied=cooldown_applied,
        resource_risk=selected.resource_risk,
    )
