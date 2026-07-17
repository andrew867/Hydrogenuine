"""Consolidated slop and quality issue detection.

Wraps rules.py detection functions and adds additional detectors for
truncation, empty content, missing units, and content length checks.

Model output is not truth. Detection results are signals, not verdicts.
"""

from __future__ import annotations

import re

from hg_runtime.output_quality.rules import (
    detect_repetitive,
    detect_circular,
    detect_generic_slop,
    detect_fake_falsification,
    detect_category_confusion,
    detect_metaphor_as_mechanism,
    detect_source_discovery_as_evidence,
    detect_unsupported_assertion,
    detect_unsafe_overclaim,
    detect_low_value_small_model,
)


def _issue(category: str, severity: str, description: str) -> dict:
    return {"category": category, "severity": severity, "description": description}


def detect_all_issues(
    content: str,
    *,
    model_id: str = "",
    mode: str = "",
    char_count: int = 0,
) -> list[dict]:
    """Run all slop/quality detectors on content. Returns list of issue dicts.

    Each issue: {"category": str, "severity": "high"|"medium"|"low", "description": str}
    """
    if char_count == 0:
        char_count = len(content) if content else 0

    issues: list[dict] = []

    # reasoning_only_empty -- content is empty or whitespace
    if not content or not content.strip():
        issues.append(_issue(
            "reasoning_only_empty", "high",
            "Content is empty or contains only whitespace.",
        ))
        return issues  # no point running other detectors on empty content

    # too_short_for_task -- content < 50 chars for non-trivial task
    if len(content.strip()) < 50:
        issues.append(_issue(
            "too_short_for_task", "medium",
            f"Content is only {len(content.strip())} chars, below 50-char minimum for non-trivial tasks.",
        ))

    # repetitive_phrasing
    if detect_repetitive(content):
        issues.append(_issue(
            "repetitive_phrasing", "medium",
            "Repetitive phrasing detected in output.",
        ))

    # circular_answer
    if detect_circular(content):
        issues.append(_issue(
            "circular_answer", "medium",
            "Circular answer detected -- conclusion restates introduction.",
        ))

    # generic_filler
    if detect_generic_slop(content):
        issues.append(_issue(
            "generic_filler", "low",
            "Generic filler phrases detected.",
        ))

    # fake_falsification
    if detect_fake_falsification(content):
        issues.append(_issue(
            "fake_falsification", "high",
            "Claims falsification without measurable criteria.",
        ))

    # category_confusion
    if detect_category_confusion(content):
        issues.append(_issue(
            "category_confusion", "medium",
            "Known physics confused with speculative claims.",
        ))

    # missing_units_or_variables -- mentions measurement/math but has no numbers
    lower = content.lower()
    has_measurement_words = any(
        w in lower for w in [
            "measurement", "measure", "frequency", "wavelength", "amplitude",
            "velocity", "mass", "energy", "temperature", "pressure",
            "calculate", "compute", "equation", "formula",
        ]
    )
    has_numbers = bool(re.search(r'\d', content))
    if has_measurement_words and not has_numbers:
        issues.append(_issue(
            "missing_units_or_variables", "medium",
            "Content mentions measurement or math concepts but contains no numbers.",
        ))

    # unsupported_assertion
    if detect_unsupported_assertion(content):
        issues.append(_issue(
            "unsupported_assertion", "high",
            "Strong claims made without supporting evidence or sources.",
        ))

    # source_without_distinction
    if detect_source_discovery_as_evidence(content):
        issues.append(_issue(
            "source_without_distinction", "medium",
            "Source discovery treated as evidence without distinction.",
        ))

    # consciousness_overclaim and manifestation_overclaim
    overclaim_terms = detect_unsafe_overclaim(content)
    consciousness_terms = {"conscious", "consciousness", "sentient", "sentience",
                           "agi", "artificial general intelligence", "alive",
                           "autonomous life", "sovereign"}
    physics_terms = {"new physics discovered", "proved new physics",
                     "self-directed external action"}

    found_consciousness = [t for t in overclaim_terms if t in consciousness_terms]
    found_physics = [t for t in overclaim_terms if t in physics_terms]

    if found_consciousness:
        issues.append(_issue(
            "consciousness_overclaim", "high",
            f"Consciousness/AGI overclaim detected: {', '.join(found_consciousness)}",
        ))
    if found_physics:
        issues.append(_issue(
            "manifestation_overclaim", "high",
            f"Physics overclaim detected: {', '.join(found_physics)}",
        ))

    # metaphor_as_mechanism
    if detect_metaphor_as_mechanism(content):
        issues.append(_issue(
            "metaphor_as_mechanism", "medium",
            "Metaphor used as if it were a causal mechanism.",
        ))

    # truncated -- content ends mid-sentence (no terminal punctuation in last 100 chars)
    tail = content.strip()[-100:] if len(content.strip()) >= 100 else content.strip()
    if tail and not re.search(r'[.!?]', tail):
        issues.append(_issue(
            "truncated", "medium",
            "Content appears truncated -- no terminal punctuation in final 100 characters.",
        ))

    # low_value_small_model
    if detect_low_value_small_model(content, model_id, char_count):
        issues.append(_issue(
            "low_value_small_model", "low",
            f"Low-value output from small model '{model_id}' with {char_count} chars.",
        ))

    return issues
