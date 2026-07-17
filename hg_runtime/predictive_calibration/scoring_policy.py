"""Calibration scoring policy.

Maps synthetic outcome kinds to calibration score kinds. A calibration record
is not proof — it measures fixture-only prediction performance only.
"""

from __future__ import annotations

OUTCOME_TO_SCORE = {
    "SYNTHETIC_MATCH": ("EXACT_MATCH", 1.0, "synthetic_exact_match_not_truth"),
    "SYNTHETIC_MISMATCH": ("MISMATCH", 0.0, "synthetic_mismatch_visible"),
    "SYNTHETIC_PARTIAL": ("PARTIAL_MATCH", 0.5, "synthetic_partial_match_provisional"),
    "SYNTHETIC_UNKNOWN": ("UNKNOWN", None, "synthetic_unknown_uncertain"),
}


def score_kind_for_outcome(outcome_kind: str) -> tuple[str, float | None, str]:
    if outcome_kind not in OUTCOME_TO_SCORE:
        raise ValueError(f"unknown_outcome_kind:{outcome_kind}")
    return OUTCOME_TO_SCORE[outcome_kind]
