"""Operator review queue builder."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hg_runtime.operator_review.review_store import ReviewStore
from hg_runtime.operator_review.schema import (
    FreshnessStatus,
    OperatorReviewItem,
    OperatorReviewQueueSnapshot,
    ReviewItemStatus,
    ReviewQueueVerdict,
    _expires_from_now,
    new_review_item_id,
    new_snapshot_id,
    now_iso,
)
from hg_runtime.operator_review.truth_state import assess_source_freshness, build_review_item_truth_state
from hg_runtime.output_artifacts.artifact_store import ArtifactStore, run_artifact_dir


def _map_candidate_status(raw: str) -> ReviewItemStatus:
    mapping = {
        "queued": ReviewItemStatus.QUEUED,
        "needs_edit": ReviewItemStatus.NEEDS_EDIT,
        "rejected": ReviewItemStatus.REJECTED,
        "superseded": ReviewItemStatus.SUPERSEDED,
        "held": ReviewItemStatus.HELD,
        "archived": ReviewItemStatus.ARCHIVED,
    }
    return mapping.get(raw, ReviewItemStatus.QUEUED)


def _load_quality_receipt(store: ArtifactStore, quality_receipt_ref: str) -> dict[str, Any] | None:
    path = store.quality_dir / f"{quality_receipt_ref}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_review_queue_snapshot(
    run_id: str,
    artifact_store_path: Path | None = None,
    *,
    review_base: Path | None = None,
    artifact_base: Path | None = None,
    offline_fixture: bool = False,
    fixture_label: str | None = None,
) -> OperatorReviewQueueSnapshot:
    """Build review queue from Phase 9 review candidates."""
    art_root = artifact_store_path or run_artifact_dir(run_id, base=artifact_base)
    manifest_path = art_root / "manifest.jsonl"
    source_store_ref = str(art_root)

    if not manifest_path.is_file():
        return OperatorReviewQueueSnapshot(
            snapshot_id=new_snapshot_id(),
            run_id=run_id,
            item_count=0,
            items=[],
            source_store_ref=source_store_ref,
            freshness_status=FreshnessStatus.MISSING,
            generated_at=now_iso(),
            expires_at=_expires_from_now(),
            verdict=ReviewQueueVerdict.RED_REVIEW_QUEUE_EMPTY_GREEN_WITHOUT_SOURCE,
        ).with_hash()

    freshness = assess_source_freshness(manifest_path)
    artifact_store = ArtifactStore(run_id, base=artifact_base)
    review_store = ReviewStore(run_id, base=review_base)
    candidates = artifact_store.list_candidates()
    generated = now_iso()
    items: list[OperatorReviewItem] = []

    for cand in candidates:
        artifact_ref = cand.get("artifact_ref", "")
        artifact_hash = cand.get("artifact_hash", "")
        quality_ref = cand.get("quality_receipt_ref", "")
        if not artifact_ref or not artifact_hash or not quality_ref:
            continue
        try:
            artifact = artifact_store.read_artifact(artifact_ref)
        except Exception:
            continue
        quality = _load_quality_receipt(artifact_store, quality_ref)
        if not quality:
            continue
        source_refs = list(artifact.get("source_refs") or [])
        provider_refs = list(artifact.get("provider_receipt_refs") or [])
        if not source_refs:
            continue

        existing = review_store.find_item_by_candidate(cand["candidate_id"])
        if existing:
            review_item_id = existing["review_item_id"]
            status = _map_candidate_status(existing.get("status", "queued"))
            truth_ref = existing.get("truth_state_ref", "")
            created_at = existing.get("created_at", generated)
        else:
            review_item_id = new_review_item_id()
            status = _map_candidate_status(cand.get("review_status", "queued"))
            created_at = generated
            truth = build_review_item_truth_state(
                review_item_ref=review_item_id,
                artifact=artifact,
                quality_receipt=quality,
                source_freshness=freshness,
                offline_fixture=offline_fixture,
                fixture_label=fixture_label,
            )
            review_store.store_truth_state(truth)
            truth_ref = truth.truth_state_id
            item = OperatorReviewItem(
                review_item_id=review_item_id,
                candidate_ref=cand["candidate_id"],
                artifact_ref=artifact_ref,
                artifact_hash=artifact_hash,
                quality_receipt_ref=quality_ref,
                source_refs=source_refs,
                provider_receipt_refs=provider_refs,
                turn_receipt_ref=artifact.get("turn_receipt_ref"),
                broker_decision_ref=artifact.get("broker_decision_ref"),
                surface=cand.get("surface") or artifact.get("surface"),
                status=status,
                created_at=created_at,
                updated_at=generated,
                truth_state_ref=truth_ref,
            ).with_hash()
            review_store.store_review_item(item)
            items.append(item)
            continue

        item = OperatorReviewItem(
            review_item_id=review_item_id,
            candidate_ref=cand["candidate_id"],
            artifact_ref=artifact_ref,
            artifact_hash=artifact_hash,
            quality_receipt_ref=quality_ref,
            source_refs=source_refs,
            provider_receipt_refs=provider_refs,
            turn_receipt_ref=artifact.get("turn_receipt_ref"),
            broker_decision_ref=artifact.get("broker_decision_ref"),
            surface=cand.get("surface") or artifact.get("surface"),
            status=status,
            created_at=created_at,
            updated_at=generated,
            truth_state_ref=truth_ref,
        ).with_hash()
        items.append(item)

    if not items:
        if freshness == FreshnessStatus.MISSING:
            verdict = ReviewQueueVerdict.RED_REVIEW_QUEUE_EMPTY_GREEN_WITHOUT_SOURCE
        elif freshness == FreshnessStatus.STALE:
            verdict = ReviewQueueVerdict.YELLOW_REVIEW_QUEUE_STALE
        else:
            verdict = ReviewQueueVerdict.YELLOW_REVIEW_QUEUE_EMPTY_FRESH
    elif freshness == FreshnessStatus.STALE:
        verdict = ReviewQueueVerdict.YELLOW_REVIEW_QUEUE_STALE
    else:
        verdict = ReviewQueueVerdict.GREEN_REVIEW_QUEUE_READY

    snapshot = OperatorReviewQueueSnapshot(
        snapshot_id=new_snapshot_id(),
        run_id=run_id,
        item_count=len(items),
        items=items,
        source_store_ref=source_store_ref,
        freshness_status=freshness,
        generated_at=generated,
        expires_at=_expires_from_now(),
        verdict=verdict,
    ).with_hash()
    review_store.store_snapshot(snapshot)
    return snapshot


def snapshot_item_summaries(snapshot: OperatorReviewQueueSnapshot, artifact_store: ArtifactStore) -> list[dict[str, Any]]:
    summaries = []
    for item in snapshot.items:
        try:
            artifact = artifact_store.read_artifact(item.artifact_ref)
            quality_path = artifact_store.quality_dir / f"{item.quality_receipt_ref}.json"
            quality = json.loads(quality_path.read_text(encoding="utf-8")) if quality_path.is_file() else {}
        except Exception:
            artifact = {}
            quality = {}
        summaries.append({
            "review_item_id": item.review_item_id,
            "candidate_ref": item.candidate_ref,
            "status": item.status.value,
            "artifact_body_preview": artifact.get("body_preview", ""),
            "quality_verdict": quality.get("verdict", "UNKNOWN"),
            "source_ref_count": len(item.source_refs),
            "provider_receipt_ref_count": len(item.provider_receipt_refs),
            "truth_state_ref": item.truth_state_ref,
            "artifact_hash": item.artifact_hash,
        })
    return summaries


__all__ = ["build_review_queue_snapshot", "snapshot_item_summaries"]
