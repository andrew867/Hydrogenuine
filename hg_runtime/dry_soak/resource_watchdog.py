"""Dry soak resource watchdog — restricts turn rate only, never expands authority."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from hg_runtime.dry_soak.schema import DrySoakResourceSnapshot, now_iso
from hg_runtime.output_artifacts.artifact_store import ArtifactStore
from hg_runtime.operator_review.review_queue import build_review_queue_snapshot


def _disk_free(path: Path) -> int | None:
    try:
        usage = shutil.disk_usage(path)
        return int(usage.free)
    except OSError:
        return None


def collect_resource_snapshot(
    *,
    run_id: str,
    turn_index: int,
    turn_duration_seconds: float,
    turn_base: Path | None = None,
    review_base: Path | None = None,
    dry_soak_root: Path | None = None,
) -> DrySoakResourceSnapshot:
    artifact_count = 0
    review_count = 0
    verdict = "GREEN_RESOURCE_OK"

    try:
        store = ArtifactStore(run_id, base=turn_base)
        if store.manifest_path.is_file():
            manifest = store.read_manifest()
            artifact_count = sum(1 for m in manifest if m.get("kind") == "artifact")
            review_count = sum(1 for m in manifest if m.get("kind") == "review_candidate")
    except Exception:
        verdict = "YELLOW_RESOURCE_METRICS_PARTIAL"

    try:
        snap = build_review_queue_snapshot(run_id, artifact_base=turn_base, review_base=review_base)
        review_count = max(review_count, snap.item_count)
    except Exception:
        if verdict == "GREEN_RESOURCE_OK":
            verdict = "YELLOW_RESOURCE_METRICS_PARTIAL"

    disk = _disk_free(dry_soak_root or Path.cwd())
    if disk is not None and disk < 100 * 1024 * 1024:
        verdict = "YELLOW_DRY_SOAK_RESOURCE_PRESSURE"

    return DrySoakResourceSnapshot(
        run_id=run_id,
        turn_index=turn_index,
        observed_at=now_iso(),
        artifact_count=artifact_count,
        review_queue_count=review_count,
        turn_duration_seconds=turn_duration_seconds,
        disk_free_bytes=disk,
        verdict=verdict,
    ).with_hash()


def adjusted_turn_interval(base_interval: float, snapshot: DrySoakResourceSnapshot) -> float:
    """Increase interval under resource pressure; never decrease safety bounds."""
    if snapshot.verdict == "YELLOW_DRY_SOAK_RESOURCE_PRESSURE":
        return max(base_interval, base_interval * 2, 1.0)
    return base_interval


__all__ = ["adjusted_turn_interval", "collect_resource_snapshot"]
