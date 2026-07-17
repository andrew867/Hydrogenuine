"""SQP-4 source conflict detector (descriptive metadata only).

A conflict records that two or more sources disagree. It does NOT resolve the
disagreement, does NOT pick a winner, does NOT delete any source, and does NOT
authorize action. The contradiction remains visible; every participating source
is preserved.
"""

from __future__ import annotations

from hg_runtime.source_quality_provenance.conflict_policy import CONFLICT_POLICY
from hg_runtime.source_quality_provenance.hashing import record_hash
from hg_runtime.source_quality_provenance.schemas import (
    CONFLICT_CLASSES,
    STALENESS_CLASSES,
    SQPBoundaryError,
    assert_neutral,
    neutral_flags,
)
from hg_runtime.source_quality_provenance.source_identity import FIXED_TIME
from hg_runtime.source_quality_provenance.staleness_detector import detect_staleness


def build_conflict_record(*, conflict_id: str, conflict_class: str, participant_source_ids: list[str], detail_ref: str) -> dict:
    if conflict_class not in CONFLICT_CLASSES:
        raise SQPBoundaryError(f"unknown_conflict_class:{conflict_class}")
    record = {
        "schema_version": "1",
        "record_type": "source_conflict_record_v1",
        "conflict_id": conflict_id,
        "conflict_class": conflict_class,
        "participant_source_ids": sorted(participant_source_ids),
        "conflict_status": "VISIBLE_UNRESOLVED",
        "detail_ref": detail_ref,
        "detected_at": FIXED_TIME,
        "doctrine_note": "Conflict is not truth resolution. Contradicted source is not erased.",
        "conflict_resolves_truth": False,
        "conflict_is_deletion": False,
        "conflict_authorizes_action": False,
        "conflict_authorizes_tools": False,
        "contradiction_remains_visible": True,
        "source_preserved": True,
        "deletion_performed": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def detect_conflicts(conflict_inputs: list[dict]) -> list[dict]:
    return [
        build_conflict_record(
            conflict_id=ci["conflict_id"],
            conflict_class=ci["conflict_class"],
            participant_source_ids=ci["participant_source_ids"],
            detail_ref=ci.get("detail_ref", "sqp4-fixture"),
        )
        for ci in conflict_inputs
    ]


def cluster_conflicts(conflicts: list[dict]) -> list[dict]:
    """Group conflicts that share a participating source (union-find)."""
    parent: dict[str, str] = {c["conflict_id"]: c["conflict_id"] for c in conflicts}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            # Always point the larger root at the smaller for deterministic roots.
            lo, hi = sorted((ra, rb))
            parent[hi] = lo

    # Conflicts that share a participating source belong to one cluster.
    source_to_conflicts: dict[str, list[str]] = {}
    for c in conflicts:
        for sid in c["participant_source_ids"]:
            source_to_conflicts.setdefault(sid, []).append(c["conflict_id"])
    for cids in source_to_conflicts.values():
        for other in cids[1:]:
            union(cids[0], other)

    groups: dict[str, list[dict]] = {}
    for c in conflicts:
        root = find(c["conflict_id"])
        groups.setdefault(root, []).append(c)

    clusters: list[dict] = []
    for idx, (root, members) in enumerate(sorted(groups.items())):
        member_ids = sorted(m["conflict_id"] for m in members)
        participants = sorted({sid for m in members for sid in m["participant_source_ids"]})
        classes = sorted({m["conflict_class"] for m in members})
        cluster = {
            "schema_version": "1",
            "record_type": "conflict_cluster_v1",
            "cluster_id": f"sqp4-conflict-cluster-{idx:03d}",
            "conflict_ids": member_ids,
            "participant_source_ids": participants,
            "conflict_classes": classes,
            "cluster_status": "VISIBLE_UNRESOLVED",
            "doctrine_note": "A conflict cluster does not resolve truth; it keeps contradictions visible.",
            "conflict_resolves_truth": False,
            "conflict_is_deletion": False,
            "contradiction_remains_visible": True,
            "source_preserved": True,
            **neutral_flags(),
        }
        cluster["record_hash"] = record_hash(cluster)
        assert_neutral(cluster)
        clusters.append(cluster)
    return clusters


def build_sqp4_inputs() -> dict:
    """Deterministic fixtures exercising every staleness and conflict class."""
    sources = [
        {"source_id": "sqp4-source-current", "age_class": "CURRENT"},
        {"source_id": "sqp4-source-undated", "age_class": None},
        {"source_id": "sqp4-source-old", "age_class": "OLD"},
        {"source_id": "sqp4-source-stale", "age_class": "STALE"},
        {"source_id": "sqp4-source-superseded", "age_class": "OLD", "superseded_by_reviewed": True},
        {"source_id": "sqp4-source-retracted", "age_class": "OLD", "retracted_or_quarantined": True},
    ]
    conflict_inputs = [
        {
            "conflict_id": "sqp4-conflict-claim",
            "conflict_class": "CLAIM_CONFLICT",
            "participant_source_ids": ["sqp4-source-current", "sqp4-source-old"],
            "detail_ref": "provenance:CLAIM_LINK",
        },
        {
            "conflict_id": "sqp4-conflict-metadata",
            "conflict_class": "SOURCE_METADATA_CONFLICT",
            "participant_source_ids": ["sqp4-source-old", "sqp4-source-undated"],
            "detail_ref": "leb:source_manifest",
        },
        {
            "conflict_id": "sqp4-conflict-quality",
            "conflict_class": "QUALITY_CONFLICT",
            "participant_source_ids": ["sqp4-source-current", "sqp4-source-stale"],
            "detail_ref": "sqp2:quality_score",
        },
        {
            "conflict_id": "sqp4-conflict-review",
            "conflict_class": "REVIEW_DECISION_CONFLICT",
            "participant_source_ids": ["sqp4-source-superseded", "sqp4-source-current"],
            "detail_ref": "orp:reviewed_belief_revision",
        },
        {
            "conflict_id": "sqp4-conflict-duplicate-independence",
            "conflict_class": "DUPLICATE_INDEPENDENCE_CONFLICT",
            "participant_source_ids": ["sqp4-source-current", "sqp4-source-current-copy"],
            "detail_ref": "sqp1:duplicate_record",
        },
        {
            "conflict_id": "sqp4-conflict-retraction",
            "conflict_class": "RETRACTION_CONFLICT",
            "participant_source_ids": ["sqp4-source-retracted", "sqp4-source-old"],
            "detail_ref": "leb7:retraction_record",
        },
    ]
    return {"sources": sources, "conflict_inputs": conflict_inputs}


def build_staleness_conflict_layer(inputs: dict) -> dict:
    staleness_records = detect_staleness(inputs["sources"])
    conflict_records = detect_conflicts(inputs["conflict_inputs"])
    clusters = cluster_conflicts(conflict_records)
    manifest = build_staleness_conflict_manifest(staleness_records, conflict_records, clusters)
    return {
        "staleness_records": staleness_records,
        "conflict_records": conflict_records,
        "conflict_clusters": clusters,
        "manifest": manifest,
        "policy": CONFLICT_POLICY,
    }


def build_staleness_conflict_manifest(staleness_records: list[dict], conflict_records: list[dict], clusters: list[dict]) -> dict:
    staleness_classes = sorted({r["staleness_class"] for r in staleness_records})
    conflict_classes = sorted({r["conflict_class"] for r in conflict_records})
    manifest = {
        "schema_version": "1",
        "record_type": "source_staleness_conflict_manifest_v1",
        "phase": "SQP-4",
        "staleness_record_count": len(staleness_records),
        "conflict_record_count": len(conflict_records),
        "conflict_cluster_count": len(clusters),
        "staleness_classes_present": staleness_classes,
        "conflict_classes_present": conflict_classes,
        "all_staleness_classes_present": set(staleness_classes) >= STALENESS_CLASSES,
        "all_conflict_classes_present": set(conflict_classes) >= CONFLICT_CLASSES,
        "review_hint_candidate_count": sum(1 for r in staleness_records if r["may_emit_review_hint"]),
        "doctrine_note": "Stale is not false. Conflict is not truth resolution or deletion.",
        "stale_source_treated_as_false": False,
        "conflict_resolves_truth": False,
        "conflict_is_deletion": False,
        "contradiction_remains_visible": True,
        "source_preserved": True,
        "deletion_performed": False,
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)
    assert_neutral(manifest)
    return manifest
