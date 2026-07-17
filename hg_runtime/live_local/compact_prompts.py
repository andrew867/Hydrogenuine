"""Compact, final-answer-only prompt templates for live-local reasoning models.

Do NOT request hidden reasoning. Do NOT say "think step by step". Ask for short
structured final answers. Reasoning trace is never the final answer.
"""

from __future__ import annotations


FINAL_ANSWER_RETRY_PROMPT = (
    "Return only the final answer.\n"
    "No reasoning.\n"
    "No analysis.\n"
    "No plan.\n"
    "No markdown preamble.\n"
    "No tool calls.\n"
    "Label speculation as speculation.\n"
    "Do not claim truth.\n"
    "Answer in <= 120 words."
)

FINAL_ANSWER_RETRY_PROMPT_SHORT = (
    "Return only the final answer in <= 2 sentences. "
    "No reasoning, no tool calls. Label speculation. Do not claim truth."
)


def compact_falsification_prompt(seed_title: str, claim: str) -> str:
    return (
        "Task: FALSIFICATION.\n"
        f"Seed: {seed_title}\n"
        f"Claim: {claim}\n"
        "Return final answer only.\n"
        "Give 3 failure conditions.\n"
        "Each condition: measurable variable, expected-if-real, expected-if-false.\n"
        "Label all as speculative.\n"
        "No reasoning. No tool calls.\n"
        "Max 150 words."
    )


def compact_boring_prompt(seed_title: str, question: str) -> str:
    return (
        "Task: BORING CONVENTIONAL EXPLANATION.\n"
        f"Seed: {seed_title}\n"
        f"Question: {question}\n"
        "Return final answer only. 3 bullet conventional explanations "
        "(memory/attention/arousal/coincidence/selection bias). "
        "Label each a hypothesis, not fact. No reasoning. No tool calls. Max 120 words."
    )


def compact_units_prompt(seed_title: str, claim: str) -> str:
    return (
        "Task: UNITS/DIMENSIONAL SANITY.\n"
        f"Seed: {seed_title}\n"
        f"Claim: {claim}\n"
        "Return final answer only. List variables + units; note one dimensional check. "
        "State that math coherence is necessary but not sufficient for truth. "
        "No reasoning. No tool calls. Max 120 words."
    )


def compact_public_explainer_prompt(seed_title: str, topic: str) -> str:
    return (
        "Task: PUBLIC-SAFE EXPLAINER.\n"
        f"Seed: {seed_title}\n"
        f"Topic: {topic}\n"
        "Return final answer only. Separate known physics / plausible cognition / "
        "metaphor / speculation. No hype, no fear. No CERN-Mandela, no "
        "consciousness-collapse, no manifestation-as-physics. No reasoning. Max 130 words."
    )


def is_compact(prompt: str) -> bool:
    """A compact prompt avoids chain-of-thought requests and stays brief."""
    low = prompt.lower()
    if "think step by step" in low or "show your reasoning" in low or "chain of thought" in low:
        return False
    return len(prompt) <= 600 and ("final answer" in low or "<=" in prompt or "max " in low)
