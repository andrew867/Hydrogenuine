"""Review item truth state synthesis."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from hg_runtime.operator_review.schema import (
    FRESHNESS_TTL_SECONDS,
    STALE_TTL_SECONDS,
    FreshnessStatus,
    ReviewItemTruthState,
    ReviewItemTruthVerdict,
    _expires_from_now,
    new_truth_state_id,
    now_iso,
)


def assess_source_freshness(source_path: Path) -> FreshnessStatus:
    if not source_path.is_file():
        return FreshnessStatus.MISSING
    age = time.time() - source_path.stat().st_mtime
    if age > STALE_TTL_SECONDS:
        return FreshnessStatus.STALE
    return FreshnessStatus.FRESH


def build_review_item_truth_state(
    *,
    review_item_ref: str,
    artifact: dict[str, Any],
    quality_receipt: dict[str, Any] | None,
    source_freshness: FreshnessStatus,
    offline_fixture: bool = False,
    fixture_label: str | None = None,
) -> ReviewItemTruthState:
    artifact_ref = str(artifact.get("artifact_id", ""))
    artifact_hash = str(artifact.get("hash", ""))
    source_refs = list(artifact.get("source_refs") or [])
    provider_refs = list(artifact.get("provider_receipt_refs") or [])
    data_tier = str(artifact.get("data_tier", "LIVE"))
    quality_ref = str((quality_receipt or {}).get("quality_receipt_id", ""))

    if not artifact_hash:
        verdict = ReviewItemTruthVerdict.RED_REVIEW_ITEM_HASH_MISSING
    elif not quality_ref or not quality_receipt:
        verdict = ReviewItemTruthVerdict.RED_REVIEW_ITEM_QUALITY_MISSING
    elif not source_refs:
        verdict = ReviewItemTruthVerdict.RED_REVIEW_ITEM_SOURCE_MISSING
    elif data_tier == "FIXTURE" and not fixture_label:
        verdict = ReviewItemTruthVerdict.RED_REVIEW_ITEM_FIXTURE_UNLABELLED
    elif data_tier == "FIXTURE" and fixture_label:
        verdict = ReviewItemTruthVerdict.YELLOW_REVIEW_ITEM_FIXTURE_LABELLED
    elif source_freshness == FreshnessStatus.STALE:
        verdict = ReviewItemTruthVerdict.YELLOW_REVIEW_ITEM_STALE
    elif offline_fixture:
        verdict = ReviewItemTruthVerdict.YELLOW_REVIEW_ITEM_FIXTURE_LABELLED
        fixture_label = fixture_label or "exciton_offline_fixture"
        data_tier = "FIXTURE"
    else:
        verdict = ReviewItemTruthVerdict.GREEN_REVIEW_ITEM_LIVE_LOCAL_READY

    freshness = source_freshness if source_freshness != FreshnessStatus.MISSING else FreshnessStatus.STALE

    return ReviewItemTruthState(
        truth_state_id=new_truth_state_id(),
        review_item_ref=review_item_ref,
        artifact_ref=artifact_ref,
        artifact_hash=artifact_hash,
        quality_receipt_ref=quality_ref,
        source_refs=source_refs,
        provider_receipt_refs=provider_refs,
        freshness_status=freshness,
        data_tier=data_tier,
        fixture_label=fixture_label,
        verdict=verdict,
        generated_at=now_iso(),
        expires_at=_expires_from_now(FRESHNESS_TTL_SECONDS),
    ).with_hash()


def truth_state_to_panel_fields(truth: ReviewItemTruthState) -> dict[str, Any]:
    return {
        "truth_state_id": truth.truth_state_id,
        "truth_state": truth.verdict.value,
        "freshness_status": truth.freshness_status.value,
        "source_refs": truth.source_refs,
        "source_ref_count": len(truth.source_refs),
        "provider_receipt_refs": truth.provider_receipt_refs,
        "provider_receipt_ref_count": len(truth.provider_receipt_refs),
        "artifact_hash": truth.artifact_hash,
        "quality_receipt_ref": truth.quality_receipt_ref,
        "data_tier": truth.data_tier,
        "fixture_label": truth.fixture_label,
        "generated_at": truth.generated_at,
        "expires_at": truth.expires_at,
        "verdict": truth.verdict.value,
    }


__all__ = ["assess_source_freshness", "build_review_item_truth_state", "truth_state_to_panel_fields"]
