"""Artifact builders."""

from __future__ import annotations

from hg_runtime.output_artifacts.schema import (
    ArtifactKind,
    ArtifactSourceBinding,
    ArtifactStatus,
    DraftArtifact,
    NotesArtifact,
    ThreadContinuationArtifact,
    body_hash,
    body_preview,
    new_artifact_id,
    now_iso,
)


def build_draft_artifact(
    *,
    body: str,
    source_binding: ArtifactSourceBinding,
    provider_receipt_refs: list[str],
    broker_decision_ref: str,
    surface: str | None = None,
    title: str | None = None,
    reasoning_receipt_ref: str | None = None,
    data_tier: str = "internal",
) -> DraftArtifact:
    return DraftArtifact(
        artifact_id=new_artifact_id(),
        kind=ArtifactKind.DRAFT,
        surface=surface,
        title=title,
        body=body,
        body_hash=body_hash(body),
        body_preview=body_preview(body),
        source_refs=source_binding.source_refs(),
        provider_receipt_refs=list(provider_receipt_refs),
        reasoning_receipt_ref=reasoning_receipt_ref,
        broker_decision_ref=broker_decision_ref,
        data_tier=data_tier,
        created_at=now_iso(),
        status=ArtifactStatus.CREATED,
    ).with_hash()


def build_notes_artifact(
    *,
    body: str,
    source_binding: ArtifactSourceBinding,
    provider_receipt_refs: list[str],
    broker_decision_ref: str | None = None,
    title: str | None = None,
) -> NotesArtifact:
    return NotesArtifact(
        artifact_id=new_artifact_id(),
        kind=ArtifactKind.NOTES,
        title=title,
        body=body,
        body_hash=body_hash(body),
        body_preview=body_preview(body),
        source_refs=source_binding.source_refs(),
        provider_receipt_refs=list(provider_receipt_refs),
        broker_decision_ref=broker_decision_ref,
        created_at=now_iso(),
        status=ArtifactStatus.CREATED,
    ).with_hash()


def build_thread_continuation_artifact(
    *,
    body: str,
    thread_ref: str,
    source_binding: ArtifactSourceBinding,
    provider_receipt_refs: list[str],
    broker_decision_ref: str | None = None,
) -> ThreadContinuationArtifact:
    return ThreadContinuationArtifact(
        artifact_id=new_artifact_id(),
        kind=ArtifactKind.THREAD_CONTINUATION,
        thread_ref=thread_ref,
        body=body,
        body_hash=body_hash(body),
        body_preview=body_preview(body),
        source_refs=source_binding.source_refs(),
        provider_receipt_refs=list(provider_receipt_refs),
        broker_decision_ref=broker_decision_ref,
        created_at=now_iso(),
        status=ArtifactStatus.CREATED,
    ).with_hash()


__all__ = [
    "build_draft_artifact",
    "build_notes_artifact",
    "build_thread_continuation_artifact",
]
