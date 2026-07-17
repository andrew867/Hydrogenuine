"""Public-safe proof summary builder.

Generates summaries safe for external audiences.
No AGI/conscious/sentient/sovereign/truth-engine claims.
"""

from __future__ import annotations

from hg_runtime.post_run_review.live_model_review_builder import (
    check_text_for_unsafe_terms,
    _UNSAFE_TERMS,
)

UNSAFE_TERMS = _UNSAFE_TERMS


def validate_public_text(text: str) -> dict:
    """Validate text is safe for public use.

    Returns dict with is_safe, flagged_terms, and recommendation.
    """
    flagged = check_text_for_unsafe_terms(text)
    return {
        "is_safe": len(flagged) == 0,
        "flagged_terms": flagged,
        "recommendation": (
            "Text is safe for public use."
            if not flagged
            else f"Remove or rephrase: {', '.join(flagged)}"
        ),
    }
