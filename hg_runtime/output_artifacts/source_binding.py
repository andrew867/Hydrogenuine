"""Source binding helpers for artifacts."""

from __future__ import annotations

from hg_runtime.output_artifacts.schema import ArtifactSourceBinding


def bind_sources(
    *,
    observe_snapshot_ref: str | None = None,
    capability_menu_ref: str | None = None,
    turn_intent_ref: str | None = None,
    reasoning_receipt_ref: str | None = None,
    live_read_receipt_refs: list[str] | None = None,
) -> ArtifactSourceBinding:
    return ArtifactSourceBinding(
        observe_snapshot_ref=observe_snapshot_ref,
        capability_menu_ref=capability_menu_ref,
        turn_intent_ref=turn_intent_ref,
        reasoning_receipt_ref=reasoning_receipt_ref,
        live_read_receipt_refs=list(live_read_receipt_refs or []),
    )


def require_source_refs(binding: ArtifactSourceBinding) -> list[str]:
    refs = binding.source_refs()
    if not refs:
        raise ValueError("RED_ARTIFACT_SOURCE_REFS_MISSING")
    return refs


__all__ = ["bind_sources", "require_source_refs"]
