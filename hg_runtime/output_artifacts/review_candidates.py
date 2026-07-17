"""Review candidate queue — local only, not approval."""

from __future__ import annotations

from hg_runtime.output_artifacts.errors import ReviewCandidateError
from hg_runtime.output_artifacts.schema import (
    ArtifactKind,
    DraftArtifact,
    OutputQualityReceipt,
    ReviewCandidate,
    ReviewCandidateStatus,
    load_artifact_review_policy,
    new_candidate_id,
    now_iso,
)


def create_review_candidate(
    *,
    artifact: DraftArtifact,
    quality_receipt: OutputQualityReceipt,
) -> ReviewCandidate:
    """Create queued review candidate from quality-passed draft."""
    policy = load_artifact_review_policy()
    if policy.get("review_candidate_is_approval"):
        raise ReviewCandidateError("review candidate cannot be approval")
    if not quality_receipt.verdict.startswith("GREEN_"):
        raise ReviewCandidateError("quality receipt must pass before review candidate")
    if not artifact.hash:
        raise ReviewCandidateError("RED_REVIEW_CANDIDATE_WITHOUT_ARTIFACT_HASH")
    if quality_receipt.artifact_hash != artifact.hash:
        raise ReviewCandidateError("artifact hash mismatch")

    return ReviewCandidate(
        candidate_id=new_candidate_id(),
        artifact_ref=artifact.artifact_id,
        artifact_hash=artifact.hash,
        quality_receipt_ref=quality_receipt.quality_receipt_id,
        surface=artifact.surface,
        review_status=ReviewCandidateStatus.QUEUED,
        operator_required=bool(policy.get("operator_required", True)),
        external_side_effect=False,
        published=False,
        sent=False,
        created_at=now_iso(),
    ).with_hash()


def should_queue_for_review(artifact_kind: ArtifactKind) -> bool:
    return artifact_kind == ArtifactKind.DRAFT


__all__ = ["create_review_candidate", "should_queue_for_review"]
