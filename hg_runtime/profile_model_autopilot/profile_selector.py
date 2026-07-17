"""Profile selector — proposes temporary cognitive profile lenses for science modes.

Never claims a profile is the person, never claims a fictional profile is real,
never grants authority, never creates persistent profile memory, never bypasses
operator constraints. Selections are advisory proposals into a task namespace.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# Science mode -> recommended abstract lens labels.
_MODE_LENS_MAP = {
    "units_and_math_audit": ["mathematical physicist", "proof auditor", "skeptical systems lens"],
    "build_the_case": ["speculative synthesizer", "creative theorist", "signal-processing lens"],
    "disprove_the_case": ["skeptical reviewer", "falsification-first scientist", "debunker lens"],
    "assume_real": ["mechanism-builder", "mathematical modeler"],
    "assume_false": ["conventional cognitive scientist", "memory researcher", "statistician"],
    "public_safe_explainer": ["public communicator", "teacher"],
    "source_discovery": ["librarian", "source critic"],
    "falsification_design": ["falsification-first scientist", "proof auditor"],
    "boring_explanation_first": ["conventional cognitive scientist", "statistician"],
    "synthesis_after_opposition": ["speculative synthesizer", "proof auditor"],
    "mechanism_builder": ["mechanism-builder", "mathematical modeler"],
    "adversarial_peer_review": ["skeptical reviewer", "proof auditor"],
}


@dataclass
class ProfileSelectionReceipt:
    task_id: str
    science_mode_id: str
    proposed_lenses: list[str] = field(default_factory=list)
    matched_profile_ids: list[str] = field(default_factory=list)
    output_namespace: str = ""
    reason: str = ""
    profile_is_identity: bool = False
    profile_grants_authority: bool = False
    creates_persistent_memory: bool = False
    creates_parallel_lifetime: bool = False
    respects_operator_constraints: bool = True


def _match_profiles(lens_labels: list[str]) -> list[str]:
    """Map abstract lens labels to concrete overlay profile ids where possible."""
    try:
        from hg_runtime.cognitive_profile_overlay.profile_loader import load_all_profiles
        profiles = load_all_profiles()
    except Exception:
        return []
    matched = []
    label_terms = {w for lab in lens_labels for w in lab.lower().split()}
    for p in profiles:
        params = " ".join(str(v) for v in p.profile_parameters.values()).lower()
        blob = (p.profile_name + " " + p.description + " " + params).lower()
        if any(term in blob for term in label_terms if len(term) > 4):
            matched.append(p.profile_id)
        if len(matched) >= 3:
            break
    return matched


def select_profiles_for_mode(
    task_id: str, science_mode_id: str, *, operator_constraints: list[str] | None = None,
) -> ProfileSelectionReceipt:
    operator_constraints = operator_constraints or []
    lenses = _MODE_LENS_MAP.get(science_mode_id, ["proof auditor"])
    # Operator constraints can remove lenses but never add authority.
    lenses = [l for l in lenses if l not in operator_constraints]
    matched = _match_profiles(lenses)
    return ProfileSelectionReceipt(
        task_id=task_id, science_mode_id=science_mode_id,
        proposed_lenses=lenses, matched_profile_ids=matched,
        output_namespace=f"autopilot::{task_id}::profile::{science_mode_id}",
        reason=f"lenses recommended for {science_mode_id}; temporary, advisory",
        profile_is_identity=False, profile_grants_authority=False,
        creates_persistent_memory=False, creates_parallel_lifetime=False,
        respects_operator_constraints=True,
    )


def recommended_lenses(science_mode_id: str) -> list[str]:
    return list(_MODE_LENS_MAP.get(science_mode_id, []))
