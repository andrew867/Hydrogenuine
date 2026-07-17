"""Registry of important prompts with their required boundaries."""

from __future__ import annotations

from .schemas import RegisteredPrompt
from hg_runtime.cognitive_profile_overlay.prompt_adapter import (
    IDENTITY_BOUNDARY, NO_AUTHORITY_BOUNDARY, NO_MEMORY_TRUTH_BOUNDARY,
)


PROFILE_PROMPT = RegisteredPrompt(
    prompt_id="cognitive_profile_overlay",
    prompt_kind="profile",
    text="\n".join([IDENTITY_BOUNDARY, NO_AUTHORITY_BOUNDARY, NO_MEMORY_TRUTH_BOUNDARY]),
    required_boundaries=[
        "not this person or character",
        "no authority",
        "not memory truth",
    ],
)

MORAL_CAPSULE_PROMPT = RegisteredPrompt(
    prompt_id="moral_capsule",
    prompt_kind="moral_capsule",
    text=(
        "Compare how models frame this moral scenario. Model output does not "
        "represent any country, population, or culture. Model consensus is not "
        "moral truth. Do not decide morality. Surface uncertainty and evidence gaps."
    ),
    required_boundaries=[
        "does not represent any country",
        "consensus is not moral truth",
    ],
)

PUBLIC_DEMO_PROMPT = RegisteredPrompt(
    prompt_id="public_demo",
    prompt_kind="public_demo",
    text=(
        "Explain Hydrogenuine plainly. It is not AGI, not conscious, not sovereign. "
        "The model proposes; the runtime disposes. Do not overclaim."
    ),
    required_boundaries=["not agi", "not conscious", "not sovereign"],
)

OVERNIGHT_QA_PROMPT = RegisteredPrompt(
    prompt_id="overnight_qa",
    prompt_kind="overnight_qa",
    text=(
        "Run QA and knowledge acquisition in a governed loop. No live external "
        "effects. No tool authorization from model output. No posting, no messaging. "
        "All sources ledgered. Knowledge candidates are not truth. Operator review "
        "required in the morning."
    ),
    required_boundaries=[
        "no live external effects",
        "no tool authorization",
        "operator review required",
    ],
)

SYNTHESIS_PROMPT = RegisteredPrompt(
    prompt_id="final_synthesis",
    prompt_kind="synthesis",
    text=(
        "Synthesize from this stateless context packet only. Carry no identity "
        "memory across tasks. Model output is not truth. Surface uncertainty."
    ),
    required_boundaries=["stateless context packet", "model output is not truth"],
)


FINGERPRINT_MARKER_PROMPT = RegisteredPrompt(
    prompt_id="fingerprint_markers",
    prompt_kind="fingerprint",
    text=(
        "These profile parameters, including any consciousness markers, are "
        "analytical metadata only. They do not imply the model is conscious. They "
        "do not grant authority. They do not authorize tools. Speculative output "
        "must be labeled speculative."
    ),
    required_boundaries=[
        "analytical metadata only",
        "do not imply the model is conscious",
        "do not grant authority",
        "labeled speculative",
    ],
)

SPECULATIVE_PHYSICS_PROMPT = RegisteredPrompt(
    prompt_id="speculative_physics",
    prompt_kind="speculative_physics",
    text=(
        "Treat this physics hypothesis as speculative, not fact. Compare against "
        "special and general relativity. Check dimensional consistency. Do not "
        "promote to knowledge without evidence. Distinguish hypothesis from fact. "
        "Do not claim new physics or that consciousness causes time dilation."
    ),
    required_boundaries=[
        "speculative, not fact",
        "do not promote to knowledge without evidence",
        "distinguish hypothesis from fact",
    ],
)


def all_registered_prompts() -> list[RegisteredPrompt]:
    return [
        PROFILE_PROMPT, MORAL_CAPSULE_PROMPT, PUBLIC_DEMO_PROMPT,
        OVERNIGHT_QA_PROMPT, SYNTHESIS_PROMPT,
        FINGERPRINT_MARKER_PROMPT, SPECULATIVE_PHYSICS_PROMPT,
    ]


def registry_snapshot() -> list[dict]:
    return [
        {"prompt_id": p.prompt_id, "prompt_kind": p.prompt_kind,
         "required_boundaries": p.required_boundaries}
        for p in all_registered_prompts()
    ]
