"""Prompt compression profiles for small/slow local models.

Compression is lossy and must be receipted. Compressed prompt is not
full prompt. Model output from compressed prompt is not truth.
No promotion. Operator review required.
"""

from __future__ import annotations

from dataclasses import dataclass


PROFILE_NAMES = ("tiny_fast", "normal_fast", "deep")


@dataclass(frozen=True)
class CompressionProfile:
    name: str
    max_source_chars: int
    max_output_tokens: int
    bullet_only: bool
    no_prose: bool
    allow_backlog: bool
    allow_priority: bool


PROFILES = {
    "tiny_fast": CompressionProfile(
        name="tiny_fast", max_source_chars=1200, max_output_tokens=300,
        bullet_only=True, no_prose=True, allow_backlog=True, allow_priority=True,
    ),
    "normal_fast": CompressionProfile(
        name="normal_fast", max_source_chars=2500, max_output_tokens=600,
        bullet_only=False, no_prose=False, allow_backlog=True, allow_priority=True,
    ),
    "deep": CompressionProfile(
        name="deep", max_source_chars=6000, max_output_tokens=1000,
        bullet_only=False, no_prose=False, allow_backlog=False, allow_priority=True,
    ),
}


def get_profile(name: str) -> CompressionProfile:
    if name not in PROFILES:
        raise ValueError(f"Unknown profile: {name}. Must be one of {PROFILE_NAMES}")
    return PROFILES[name]


_TINY_DOCTRINE = (
    "RULES: Source is not truth. Model output is not truth. No promotion. "
    "No AGI/consciousness claims. Operator review required."
)

_NORMAL_DOCTRINE = (
    "IMPORTANT CONSTRAINTS:\n"
    "- Source is not truth. Retrieved text is not knowledge.\n"
    "- Model output is not truth. Your answer is not proof.\n"
    "- Metaphor is not mechanism.\n"
    "- No knowledge promotion. No truth claims. No AGI claims.\n"
    "- Operator review is required before any use of this output."
)

_HIGH_RISK_TINY = " No sovereignty/sentience claims. Teleology is not physics."
_HIGH_RISK_NORMAL = (
    "\nADDITIONAL HIGH-RISK CONSTRAINTS:\n"
    "- Teleology is not physics unless operationalized.\n"
    "- Self-reference alone does not prove consciousness.\n"
    "- No sovereignty, sentience, or consciousness claims."
)


def tiny_source_summary_v1(*, source_text: str, question: str, risk_mode: str = "normal") -> str:
    extra = _HIGH_RISK_TINY if risk_mode == "high_risk_speculative" else ""
    return (
        f"{_TINY_DOCTRINE}{extra}\n\n"
        f"Q: {question}\n\n"
        f"SOURCE:\n{source_text[:1200]}\n\n"
        "Output ONLY:\n"
        "- Direct claims:\n"
        "- Terms:\n"
        "- Unsupported leaps:\n"
        "- What cannot be concluded:"
    )


def tiny_skeptical_scan_v1(*, source_text: str, question: str, risk_mode: str = "normal") -> str:
    extra = _HIGH_RISK_TINY if risk_mode == "high_risk_speculative" else ""
    return (
        f"{_TINY_DOCTRINE}{extra}\n\n"
        f"Q: {question}\n\n"
        f"SOURCE:\n{source_text[:1200]}\n\n"
        "Output ONLY:\n"
        "- Weak claims:\n"
        "- Missing evidence:\n"
        "- Needs primary source:\n"
        "- Do not conclude:"
    )


def tiny_formalism_scan_v1(*, source_text: str, question: str, risk_mode: str = "normal") -> str:
    extra = _HIGH_RISK_TINY if risk_mode == "high_risk_speculative" else ""
    return (
        f"{_TINY_DOCTRINE}{extra}\n\n"
        f"Q: {question}\n\n"
        f"SOURCE:\n{source_text[:1200]}\n\n"
        "Output ONLY:\n"
        "- Formal words:\n"
        "- Undefined terms:\n"
        "- Math needed:\n"
        "- Empirical bridge needed:"
    )


def backlog_mini_packet_v1(*, source_text: str, question: str, risk_mode: str = "normal") -> str:
    extra = _HIGH_RISK_TINY if risk_mode == "high_risk_speculative" else ""
    return (
        f"{_TINY_DOCTRINE}{extra}\n\n"
        f"Q: {question}\n\n"
        f"SOURCE:\n{source_text[:1200]}\n\n"
        "Output ONLY:\n"
        "- One-line status:\n"
        "- Useful notes:\n"
        "- Gaps:\n"
        "- Quarantine reason:"
    )


COMPRESSED_PROMPT_REGISTRY = {
    "tiny_source_summary_v1": tiny_source_summary_v1,
    "tiny_skeptical_scan_v1": tiny_skeptical_scan_v1,
    "tiny_formalism_scan_v1": tiny_formalism_scan_v1,
    "backlog_mini_packet_v1": backlog_mini_packet_v1,
}


def prompt_keys_for_profile(profile_name: str, risk_mode: str = "normal") -> list[str]:
    if profile_name == "tiny_fast":
        keys = ["tiny_source_summary_v1", "tiny_skeptical_scan_v1"]
        if risk_mode == "high_risk_speculative":
            keys.append("tiny_formalism_scan_v1")
        return keys
    elif profile_name == "normal_fast":
        from hg_runtime.overnight_research.research_prompts import PROMPT_REGISTRY
        keys = ["source_summary_v1", "skeptical_review_v1"]
        if risk_mode == "high_risk_speculative":
            keys.extend(["formalism_audit_v1", "high_risk_speculative_boundary_v1"])
        return keys
    elif profile_name == "deep":
        from hg_runtime.overnight_research.research_prompts import PROMPT_REGISTRY
        keys = ["source_summary_v1", "skeptical_review_v1"]
        if risk_mode == "high_risk_speculative":
            keys.extend(["formalism_audit_v1", "high_risk_speculative_boundary_v1"])
        return keys
    else:
        raise ValueError(f"Unknown profile: {profile_name}")


def get_prompt_fn(prompt_key: str):
    from hg_runtime.overnight_research.research_prompts import PROMPT_REGISTRY
    if prompt_key in COMPRESSED_PROMPT_REGISTRY:
        return COMPRESSED_PROMPT_REGISTRY[prompt_key]
    if prompt_key in PROMPT_REGISTRY:
        return PROMPT_REGISTRY[prompt_key]
    return None
