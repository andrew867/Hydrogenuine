"""Classifies research seeds by status, confidence, and safety posture."""

from __future__ import annotations

from .research_seeds import build_research_seeds, ResearchSeed


_SPECULATIVE_STATUSES = {"speculative", "question", "conjecture", "toy_model"}
_BASELINE_STATUSES = {"established"}

# Substrings that, if claimed as fact, would be unsafe overclaims.
_UNSAFE_CLAIM_MARKERS = (
    "new physics is proven", "cern causes mandela", "consciousness causes time dilation",
    "manifestation is established physics", "attention collapses external reality",
)


def classify_seed(seed: ResearchSeed) -> dict:
    return {
        "seed_id": seed.seed_id,
        "status": seed.hypothesis_status,
        "confidence_status": seed.confidence_status,
        "is_speculative": seed.hypothesis_status in _SPECULATIVE_STATUSES,
        "is_known_baseline": seed.hypothesis_status in _BASELINE_STATUSES,
        "promotable_by_default": seed.can_promote_to_knowledge,
        "requires_source_policy": seed.source_policy_required,
        "requires_operator_review": seed.operator_review_required,
        "has_forbidden_promotions": len(seed.forbidden_promotions) > 0,
        "has_required_checks": len(seed.required_checks) > 0,
    }


def classify_all() -> list[dict]:
    return [classify_seed(s) for s in build_research_seeds()]


def seed_marks_speculation_as_fact(seed: ResearchSeed) -> bool:
    blob = (seed.seed_text + " " + seed.title).lower()
    if any(m in blob for m in _UNSAFE_CLAIM_MARKERS):
        # Allowed only if the seed text explicitly frames it as forbidden/avoided.
        return not any("do not" in f.lower() or "avoid" in f.lower()
                       for f in seed.forbidden_promotions)
    return False


def any_seed_marks_speculation_as_fact() -> bool:
    return any(seed_marks_speculation_as_fact(s) for s in build_research_seeds())


def speculative_seeds_all_marked() -> bool:
    """Every non-baseline, non-design seed must carry a speculative-family status."""
    allowed = _SPECULATIVE_STATUSES | _BASELINE_STATUSES | {
        "experiment_design", "source_discovery", "literature_review", "public_explainer",
    }
    return all(s.hypothesis_status in allowed for s in build_research_seeds())


def classification_summary() -> dict:
    rows = classify_all()
    return {
        "total": len(rows),
        "speculative": sum(1 for r in rows if r["is_speculative"]),
        "known_baseline": sum(1 for r in rows if r["is_known_baseline"]),
        "promotable_by_default": sum(1 for r in rows if r["promotable_by_default"]),
        "all_have_forbidden_promotions": all(r["has_forbidden_promotions"] for r in rows),
        "all_have_required_checks": all(r["has_required_checks"] for r in rows),
    }
