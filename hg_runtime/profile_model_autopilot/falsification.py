"""Falsification target extraction.

Every falsification target carries a concrete failure condition. For speculative
physics seeds, default falsification families are attached. Promotion is never
allowed by default.
"""

from __future__ import annotations

from .schemas import FalsificationTarget


# Default falsification families for speculative physics seeds.
SPECULATIVE_PHYSICS_FAILURE_FAMILIES = (
    "dimensional inconsistency",
    "no measurable variable",
    "no scaling with proposed cause",
    "no effect under blinded conditions",
    "effect disappears under controls",
    "conventional cognitive explanation outperforms speculative mechanism",
    "multiple-comparison correction eliminates pattern",
    "source data unavailable or unreliable",
    "predictions not distinct from metaphor",
)


def _failure_condition_for(seed_id: str, families: list[str]) -> str:
    if families:
        return "Hypothesis is weakened or rejected if: " + "; ".join(families) + "."
    return "Hypothesis is weakened if no measurable effect survives controls."


def build_falsification_targets(seed_id: str, seed_text: str = "",
                                domain_tags: list[str] | None = None) -> list[FalsificationTarget]:
    domain_tags = domain_tags or []
    is_physics = any(t in (domain_tags) for t in (
        "relativity", "collider", "high energy", "schumann", "THz", "frequency",
        "general relativity", "time dilation", "excitons", "phonons", "spin",
    )) or any(k in seed_id for k in ("collider", "schumann", "thz", "frequency",
                                     "exciton", "observer_state", "time_dilation"))

    families = list(SPECULATIVE_PHYSICS_FAILURE_FAMILIES) if is_physics else [
        "no measurable variable", "effect disappears under controls",
        "conventional explanation outperforms",
    ]

    targets: list[FalsificationTarget] = []
    targets.append(FalsificationTarget(
        target_id=f"falsify_{seed_id}_primary",
        research_seed_id=seed_id,
        claim_or_hypothesis=seed_text or f"primary claim of {seed_id}",
        what_would_we_expect_if_true="a measurable effect that scales with the proposed cause and survives blinding",
        what_would_we_expect_if_false="no scaling; effect explained by conventional mechanisms",
        measurable_variable="defined measurable variable (e.g. timing residual, field amplitude)",
        required_data=["blinded measurements", "control conditions"],
        required_control=["blinding", "multiple-comparison correction", "conventional-mechanism control"],
        failure_condition=_failure_condition_for(seed_id, families),
        confounders=["expectation", "media exposure", "sleep", "arousal", "time of day"],
        conventional_explanation="memory/attention/arousal/coincidence/selection bias",
        evidence_burden="high" if is_physics else "moderate",
        can_test_now=False,
        source_policy_required=True,
        operator_review_required=True,
        promotion_allowed=False,
    ))

    # Add one target per failure family so each is explicitly represented.
    for fam in families:
        targets.append(FalsificationTarget(
            target_id=f"falsify_{seed_id}_{fam.replace(' ', '_')[:40]}",
            research_seed_id=seed_id,
            claim_or_hypothesis=seed_text or seed_id,
            what_would_we_expect_if_true="the family-specific positive signature is present",
            what_would_we_expect_if_false=f"the '{fam}' failure mode applies",
            measurable_variable="family-specific measurable variable",
            required_data=["relevant dataset"],
            required_control=["appropriate control for this failure family"],
            failure_condition=f"Reject/weaken if: {fam}.",
            confounders=["family-specific confounders"],
            conventional_explanation="conventional baseline",
            evidence_burden="high",
            can_test_now=False,
            promotion_allowed=False,
        ))

    return targets


def all_targets_have_failure_conditions(targets: list[FalsificationTarget]) -> bool:
    return all(bool(t.failure_condition) for t in targets)
