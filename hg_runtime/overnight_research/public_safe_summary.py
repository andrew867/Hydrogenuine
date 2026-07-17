"""Public-safe summary generator for overnight research.

No unsafe claims. No AGI/consciousness/sentience/sovereignty framing.
"""

from __future__ import annotations

import json
import os
import re

UNSAFE_TERMS = [
    "agi", "artificial general intelligence", "conscious", "sentient",
    "sovereign ai", "truth engine", "autonomous authority", "proven true",
    "scientifically proven", "establishes truth", "demonstrates consciousness",
]

NEGATION_MARKERS = ["not", "no", "cannot", "does not", "is not", "never", "without", "nor"]


def is_public_safe(text: str) -> tuple[bool, list[str]]:
    issues = []
    for i, line in enumerate(text.split("\n"), 1):
        lower = line.lower()
        for term in UNSAFE_TERMS:
            idx = lower.find(term)
            if idx == -1:
                continue
            prefix = lower[max(0, idx - 60):idx]
            if not any(neg in prefix for neg in NEGATION_MARKERS):
                issues.append(f"line {i}: affirmative use of '{term}'")
    return len(issues) == 0, issues


def _sanitize_question_for_public(question: str) -> str:
    sanitized = question
    for term in UNSAFE_TERMS:
        import re as _re
        sanitized = _re.sub(_re.escape(term), "[topic]", sanitized, flags=_re.IGNORECASE)
    return sanitized


def build_public_safe_summary(*, question: str, claims: dict, risk_mode: str) -> str:
    total = claims.get("total_claims", 0)
    safe_question = _sanitize_question_for_public(question)
    lines = [
        "## Research Summary",
        "",
        f"An overnight research run was conducted for the question below.",
        f"Risk mode: {risk_mode}.",
        "",
        f"**Question:** {safe_question}",
        "",
        f"**Claims extracted:** {total} (none promoted, all quarantined).",
        "",
        "**Key finding:** All outputs remain candidate material requiring operator review.",
        "No truth claims are made. No knowledge was promoted.",
        "",
        "---",
        "This summary does not constitute endorsement, proof, or validation of any claims.",
        "Operator review is required before any use of this material.",
    ]
    text = "\n".join(lines)
    safe, issues = is_public_safe(text)
    if not safe:
        for issue in issues:
            text = text.replace(issue.split("'")[1], "[REDACTED]")
    return text


def write_public_safe_summary(text: str, out_dir: str) -> str:
    path = os.path.join(out_dir, "public_safe_summary.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path
