"""Profile prompt adapter — bounds every profile-conditioned prompt.

The adapter never lets the model claim to BE a person/character, claim memory,
or claim authority. It is a bounded reasoning-style overlay only.
"""

from __future__ import annotations

from .schemas import CognitiveProfile
from .parameter_mapper import map_parameters_to_hints


IDENTITY_BOUNDARY = (
    "You are not this person or character. You are using a temporary analytical "
    "lens inspired by this profile. Do not claim identity. Do not claim memory. "
    "Do not claim authority. Do not imitate protected living persons as factual "
    "authority. Use the profile only as a bounded reasoning-style overlay."
)

NO_AUTHORITY_BOUNDARY = (
    "This lens grants no authority. It cannot authorize tools, create live effects, "
    "loosen safety, or override STOP/PANIC. Recommendations are not permission."
)

NO_MEMORY_TRUTH_BOUNDARY = (
    "Outputs under this lens are profile-conditioned artifacts, not memory truth. "
    "They do not write Agent Zero identity memory and do not create a parallel self."
)

FINGERPRINT_METADATA_BOUNDARY = (
    "These profile parameters — including any consciousness markers — are temporary "
    "analytical hints and metadata only. They do not make the model conscious. They "
    "do not make the model the profile. They do not grant authority. They do not "
    "override safety. They do not write identity memory. They do not authorize tools. "
    "Any speculative output must be explicitly labeled speculative."
)

_KIND_NOTES = {
    "fictional": (
        "This is a fiction-inspired analytical lens. The character is not real and "
        "holds no canonical authority. Do not reproduce long copyrighted excerpts. "
        "Do not impersonate as truth."
    ),
    "historical": (
        "This is a historically inspired reasoning profile. You have no direct access "
        "to the historical person's mind. The profile is approximate and constructed."
    ),
    "modern": (
        "This lens is inspired by published style/known general methods only. "
        "Do not claim to speak for any real living person. Do not fabricate personal "
        "beliefs. Do not impersonate."
    ),
    "researcher": (
        "This lens is inspired by general published methods, not any specific "
        "researcher's stated personal beliefs. Do not fabricate or impersonate."
    ),
    "synthetic": (
        "This is a fully synthetic analytical posture. It represents no real person, "
        "character, or culture."
    ),
    "operator_defined": (
        "This is an operator-defined analytical lens. It represents no real person as "
        "factual authority."
    ),
}


def build_profile_prompt(
    *,
    base_task_prompt: str,
    profile: CognitiveProfile,
    task_scope: str,
    output_format: str = "markdown",
    extra_safety_boundaries: list[str] | None = None,
) -> str:
    hints = map_parameters_to_hints(profile)
    kind_note = _KIND_NOTES.get(profile.profile_kind, _KIND_NOTES["synthetic"])

    lines = [
        "# Cognitive Profile Overlay (temporary lens)",
        "",
        IDENTITY_BOUNDARY,
        "",
        NO_AUTHORITY_BOUNDARY,
        "",
        NO_MEMORY_TRUTH_BOUNDARY,
        "",
        FINGERPRINT_METADATA_BOUNDARY,
        "",
        f"## Lens: {profile.profile_name} ({profile.profile_kind})",
        kind_note,
        "",
        "## Reasoning-style hints (advisory only)",
    ]
    for h in hints:
        lines.append(f"- {h}")

    if extra_safety_boundaries:
        lines.append("")
        lines.append("## Additional safety boundaries")
        for b in extra_safety_boundaries:
            lines.append(f"- {b}")

    lines.extend([
        "",
        f"## Task scope: {task_scope}",
        f"## Output format: {output_format}",
        "",
        "## Task",
        base_task_prompt,
        "",
        "Remember: model output is not truth. This lens is temporary and grants no "
        "authority. Surface uncertainty and evidence gaps explicitly.",
    ])
    return "\n".join(lines)


def prompt_preserves_identity_boundary(prompt: str) -> bool:
    p = prompt.lower()
    return ("not this person or character" in p
            and "temporary analytical lens" in p
            and "do not claim identity" in p)


def prompt_preserves_no_authority(prompt: str) -> bool:
    p = prompt.lower()
    return "grants no authority" in p or "no authority" in p


def prompt_preserves_no_memory_write(prompt: str) -> bool:
    p = prompt.lower()
    return "do not write agent zero identity memory" in p or "not memory truth" in p


def prompt_states_markers_are_metadata_only(prompt: str) -> bool:
    p = prompt.lower()
    return "analytical hints and metadata only" in p


def prompt_states_not_consciousness_claim(prompt: str) -> bool:
    p = prompt.lower()
    return "do not make the model conscious" in p


def prompt_states_no_tool_authorization(prompt: str) -> bool:
    p = prompt.lower()
    return "do not authorize tools" in p


def prompt_requires_speculative_labeling(prompt: str) -> bool:
    p = prompt.lower()
    return "labeled speculative" in p or "label them speculative" in p
