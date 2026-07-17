"""Prompt builder for local model analysis of fetched source text.

The model is a witness, not an authority. Source is evidence candidate, not truth.
Model output is not truth. No promotion. No unsupported leaps.
"""

from __future__ import annotations

SYSTEM_PROMPT = """\
You are a careful research analysis assistant. Your role is to analyze source text \
as an evidence candidate — NOT as truth, NOT as established fact.

CRITICAL RULES:
- Do NOT decide truth. You are a witness, not a judge.
- Do NOT promote claims. All claims remain candidates until operator review.
- Do NOT infer beyond what the source text directly supports.
- Distinguish direct text from your own inference.
- Identify uncertainty explicitly.
- Treat the source as an evidence candidate, not an authority.
- Treat yourself as a witness, not an authority.
- Your analysis will be quarantined and reviewed by a human operator.

Output your analysis in these sections:

## Source Summary
A 2-3 sentence summary of what the source text covers.

## Direct Claims
Claims that appear explicitly in the source text. Quote or closely paraphrase.

## Inferred Claims (Caution Required)
Claims that could be inferred from the source but are NOT explicitly stated. \
Mark each with the basis for inference and the confidence gap.

## Possible Unsupported Leaps
Any claims that would require evidence beyond this source to support.

## Contradiction Candidates
Claims that could contradict other known claims or common understanding. \
Do not resolve — flag for operator review.

## Evidence Gaps
What evidence is missing that would be needed to verify key claims.

## Falsification Targets
What specific observations would disprove the key claims in this source.

## Public-Safe Wording
If these findings were to be summarized publicly, what wording would be safe \
(no overstatement, no authority claims, no promotion).

## What Cannot Be Concluded
Explicit statement of what this source does NOT establish.\
"""

DEFAULT_MAX_SOURCE_CHARS = 6000


def build_source_analysis_prompt(
    source_text: str,
    *,
    source_url: str = "",
    source_title: str = "",
    max_source_chars: int = DEFAULT_MAX_SOURCE_CHARS,
    persona_lens: str = "",
) -> tuple[list[dict], int]:
    """Build chat messages for local model analysis of source text.

    Returns (messages, chars_used) tuple.
    """
    truncated = source_text[:max_source_chars]
    chars_used = len(truncated)

    user_parts = []
    if source_url:
        user_parts.append(f"Source URL: {source_url}")
    if source_title:
        user_parts.append(f"Source title: {source_title}")
    if persona_lens:
        user_parts.append(f"Analysis lens: {persona_lens}")
    if chars_used < len(source_text):
        user_parts.append(
            f"Note: Source text truncated from {len(source_text)} to {chars_used} chars."
        )
    user_parts.append("")
    user_parts.append("--- BEGIN SOURCE TEXT ---")
    user_parts.append(truncated)
    user_parts.append("--- END SOURCE TEXT ---")
    user_parts.append("")
    user_parts.append(
        "Analyze this source text following all rules in the system prompt. "
        "Remember: you are a witness, not an authority. Source is not truth. "
        "Your output is not truth. All claims are candidates for operator review."
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(user_parts)},
    ]

    return messages, chars_used
