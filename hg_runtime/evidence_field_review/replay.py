"""P70 evidence field review replay."""

from __future__ import annotations

from hg_runtime.evidence_field_review.artifact_writer import build_evidence_artifacts
from hg_runtime.evidence_field_review.fixtures import (
    fixture_discrepancy_record,
    fixture_evidence_review_record,
    fixture_reproduction_packet,
    fixture_reviewer_notes,
    fixture_unresolved_gap,
)


def replay_evidence_artifacts() -> dict:
    return build_evidence_artifacts(
        [fixture_reproduction_packet()],
        [fixture_evidence_review_record()],
        [fixture_reviewer_notes()],
        [fixture_discrepancy_record()],
        [fixture_unresolved_gap()],
    )
