"""Output artifacts — local-only draft and notes layer."""

from __future__ import annotations

from hg_runtime.output_artifacts.artifact_store import ArtifactStore
from hg_runtime.output_artifacts.artifacts import (
    build_draft_artifact,
    build_notes_artifact,
    build_thread_continuation_artifact,
)
from hg_runtime.output_artifacts.output_quality import evaluate_output_quality
from hg_runtime.output_artifacts.review_candidates import create_review_candidate
from hg_runtime.output_artifacts.schema import (
    ArtifactKind,
    ArtifactVerdict,
    DraftArtifact,
    NotesArtifact,
    OutputQualityReceipt,
    ReviewCandidate,
    ThreadContinuationArtifact,
)

__all__ = [
    "ArtifactKind",
    "ArtifactStore",
    "ArtifactVerdict",
    "DraftArtifact",
    "NotesArtifact",
    "OutputQualityReceipt",
    "ReviewCandidate",
    "ThreadContinuationArtifact",
    "build_draft_artifact",
    "build_notes_artifact",
    "build_thread_continuation_artifact",
    "create_review_candidate",
    "evaluate_output_quality",
]
