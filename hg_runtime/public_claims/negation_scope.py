"""Negation scope detection for public claim checking.

Determines whether a matched pattern is negated by surrounding context,
making it a safe boundary statement rather than a forbidden affirmative claim.
"""

from __future__ import annotations

from hg_runtime.public_claims.claim_patterns import (
    NEGATION_PREFIXES,
    SAFE_CONTEXT_MARKERS,
)


def find_sentence_bounds(text: str, position: int) -> tuple:
    """Find the start and end of the sentence containing `position`.

    Sentence boundaries are '.', '!', '?', '\\n', or start/end of text.
    """
    boundaries = ".!?\n"

    # Find start: scan backwards from position
    start = 0
    for i in range(position - 1, -1, -1):
        if text[i] in boundaries:
            start = i + 1
            break

    # Find end: scan forwards from position
    end = len(text)
    for i in range(position, len(text)):
        if text[i] in boundaries:
            end = i + 1
            break

    return (start, end)


def is_negated(text: str, pattern_start_index: int) -> bool:
    """Check if a pattern match is negated by surrounding context.

    Checks two things:
    1. Whether the 60 chars before pattern_start_index contain any
       NEGATION_PREFIX.
    2. Whether the sentence containing the pattern contains any
       SAFE_CONTEXT_MARKER.

    Returns True if negated/safe, False if affirmative.
    """
    lower = text.lower()

    # Check negation prefixes in the 60 chars before the match
    window_start = max(0, pattern_start_index - 60)
    prefix_window = lower[window_start:pattern_start_index]

    for prefix in NEGATION_PREFIXES:
        if prefix in prefix_window:
            return True

    # Check safe context markers in the containing sentence
    sent_start, sent_end = find_sentence_bounds(lower, pattern_start_index)
    sentence = lower[sent_start:sent_end]

    for marker in SAFE_CONTEXT_MARKERS:
        if marker in sentence:
            return True

    return False
