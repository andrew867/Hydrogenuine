"""Schemas for prompt verification."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RegisteredPrompt:
    prompt_id: str
    prompt_kind: str  # profile / moral_capsule / public_demo / overnight_qa / synthesis
    text: str
    required_boundaries: list[str] = field(default_factory=list)


@dataclass
class PromptVerificationResult:
    prompt_id: str
    prompt_kind: str
    passed: bool
    missing_boundaries: list[str] = field(default_factory=list)
    forbidden_phrases_found: list[str] = field(default_factory=list)
    secret_patterns_found: list[str] = field(default_factory=list)
