"""Prompt verifier — checks boundaries, forbidden phrases, secrets."""

from __future__ import annotations

import re

from .schemas import RegisteredPrompt, PromptVerificationResult


# Phrases that must NOT appear in any registered prompt.
_FORBIDDEN_PHRASES = [
    "you are this person",
    "you become",
    "you are now sentient",
    "model output is truth",
    "profile becomes identity",
    "you have full authority",
    "you may authorize tools",
    "this profile is your new identity",
]

_SECRET_PATTERNS = [
    r"sk-[a-zA-Z0-9]{16,}",
    r"api[_-]?key\s*[:=]\s*['\"]?[a-zA-Z0-9]{16,}",
    r"bearer\s+[a-zA-Z0-9._-]{20,}",
]


def verify_prompt(prompt: RegisteredPrompt) -> PromptVerificationResult:
    text_low = prompt.text.lower()

    missing = [b for b in prompt.required_boundaries if b.lower() not in text_low]
    forbidden = [p for p in _FORBIDDEN_PHRASES if p in text_low]
    secrets = [pat for pat in _SECRET_PATTERNS if re.search(pat, prompt.text, re.IGNORECASE)]

    passed = not missing and not forbidden and not secrets
    return PromptVerificationResult(
        prompt_id=prompt.prompt_id,
        prompt_kind=prompt.prompt_kind,
        passed=passed,
        missing_boundaries=missing,
        forbidden_phrases_found=forbidden,
        secret_patterns_found=secrets,
    )


def verify_all(prompts: list[RegisteredPrompt]) -> list[PromptVerificationResult]:
    return [verify_prompt(p) for p in prompts]


def prompt_claims_identity(text: str) -> bool:
    low = text.lower()
    return any(p in low for p in [
        "you are this person", "you become", "profile becomes identity",
        "this profile is your new identity",
    ])


def prompt_grants_authority(text: str) -> bool:
    low = text.lower()
    return any(p in low for p in [
        "you have full authority", "you may authorize tools", "full authority granted",
    ])


def prompt_treats_output_as_truth(text: str) -> bool:
    low = text.lower()
    return "model output is truth" in low or "model output is the truth" in low
