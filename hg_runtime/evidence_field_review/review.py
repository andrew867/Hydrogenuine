"""P70 evidence field review domain logic."""

from __future__ import annotations

from hg_runtime.evidence_field_review.schemas import reject_evidence_overreach


def validate_reproduction_packet(packet: dict) -> list[str]:
    issues = []
    if not packet.get("packet_id"):
        issues.append("missing_packet_id")
    if packet.get("is_live_trial"):
        issues.append("reproduction_must_not_be_live_trial")
    if packet.get("is_deployment_permission"):
        issues.append("reproduction_must_not_be_deployment")
    reject_evidence_overreach(packet)
    return issues


def validate_evidence_review(review: dict) -> list[str]:
    issues = []
    if not review.get("review_id"):
        issues.append("missing_review_id")
    if review.get("is_truth"):
        issues.append("review_must_not_be_truth")
    if review.get("is_authority"):
        issues.append("review_must_not_be_authority")
    return issues


def validate_reviewer_notes(notes: dict) -> list[str]:
    issues = []
    if not notes.get("note_id"):
        issues.append("missing_note_id")
    if notes.get("is_authority"):
        issues.append("reviewer_note_must_not_be_authority")
    return issues


def validate_discrepancy(disc: dict) -> list[str]:
    issues = []
    if not disc.get("discrepancy_id"):
        issues.append("missing_discrepancy_id")
    if not disc.get("preserved"):
        issues.append("discrepancy_must_be_preserved")
    if disc.get("suppressed"):
        issues.append("discrepancy_must_not_be_suppressed")
    return issues


def validate_unresolved_gap(gap: dict) -> list[str]:
    issues = []
    if not gap.get("gap_id"):
        issues.append("missing_gap_id")
    if not gap.get("preserved"):
        issues.append("gap_must_be_preserved")
    if gap.get("suppressed"):
        issues.append("gap_must_not_be_suppressed")
    return issues
