"""P26 gap mapper: assign a gap status to each acceptance criterion.

Gap analysis is not completion. A SATISFIED_BY_EXISTING_ARTIFACT status means an
existing artifact bears on the criterion, NOT that P26 is complete. P26 completion
requires an exact P26 gate/report/proof, which does not exist (P26-AC-8 is
REQUIRES_EXACT_P26_IMPLEMENTATION).
"""

from __future__ import annotations

from pathlib import Path

from hg_runtime.generalist_gap_reconciliation.acceptance_criteria_reader import read_acceptance_criteria
from hg_runtime.generalist_gap_reconciliation.existing_artifact_mapper import build_existing_artifact_map
from hg_runtime.generalist_gap_reconciliation.schemas import (
    GAP_STATUSES,
    NON_COMPLETING_STATUSES,
    PHASE19_VERDICT,
    PHASE24_STATUS,
    P26GapBoundaryError,
    assert_neutral,
    neutral_flags,
    record_hash,
)

# Deterministic status + recommendation per criterion.
_GAP_DECISION = {
    "P26-AC-1": ("PARTIALLY_SATISFIED", "Ledger primitives (hash chain) and LEB receipts exist; a unified experience ledger is not yet defined."),
    "P26-AC-2": ("PARTIALLY_SATISFIED", "SQP provenance covers evidence sources, not a dedicated memory ledger; extend provenance to memory entries."),
    "P26-AC-3": ("SATISFIED_BY_EXISTING_ARTIFACT", "Deterministic replay is proven by RC and extended soak; reuse the replay harness for a memory ledger."),
    "P26-AC-4": ("SATISFIED_BY_EXISTING_ARTIFACT", "LEB-7 append-only retraction/quarantine without erasure can back P26 memory retraction."),
    "P26-AC-5": ("MISSING", "No cross-session persistent recall API exists; a scoped recall surface is needed (read-only first)."),
    "P26-AC-6": ("PARTIALLY_SATISFIED", "ORP operator-gated belief revision covers evidence; a P26 experience-to-belief gate must reuse the same operator-review discipline."),
    "P26-AC-7": ("SATISFIED_BY_EXISTING_ARTIFACT", "Decay-not-erasure exists (WMBR-06 / LEB decay); reuse for memory decay policy."),
    "P26-AC-8": ("REQUIRES_EXACT_P26_IMPLEMENTATION", "No unified P26 gate/report/proof exists; a narrow P26 implementation phase is required for completion."),
    "P26-AC-9": ("INCOMPATIBLE", "Live autonomous memory writes conflict with the current no-live-effect boundary; remains forbidden until a separate gated lane exists."),
    "P26-AC-10": ("OUT_OF_SCOPE", "Self-directed cross-agent memory curation is a candidate-AGI lane; out of scope for the bounded local runtime."),
}


def build_gap_record(*, criterion_id: str, title: str, status: str, artifact_present: bool, rationale: str) -> dict:
    if status not in GAP_STATUSES:
        raise P26GapBoundaryError(f"unknown_gap_status:{status}")
    record = {
        "schema_version": "1",
        "record_type": "p26_gap_record_v1",
        "criterion_id": criterion_id,
        "title": title,
        "gap_status": status,
        "artifact_present": artifact_present,
        "rationale": rationale,
        "counts_as_p26_completion": False,
        "doctrine_note": "Gap analysis is not completion; partial satisfaction is not GREEN for P26.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_recommendation_record(*, criterion_id: str, status: str, recommendation: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "p26_recommendation_record_v1",
        "criterion_id": criterion_id,
        "gap_status": status,
        "recommendation": recommendation,
        "requires_operator_review": True,
        "auto_implementable": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_p26_layer(root: Path) -> dict:
    criteria = read_acceptance_criteria()
    artifact_map = build_existing_artifact_map(root)
    present_by_id = {e["criterion_id"]: e["any_artifact_present"] for e in artifact_map}
    criteria_map = {c["criterion_id"]: c for c in criteria}

    gap_records = []
    recommendations = []
    for criterion_id, (status, rationale) in _GAP_DECISION.items():
        title = criteria_map[criterion_id]["title"]
        gap_records.append(
            build_gap_record(
                criterion_id=criterion_id,
                title=title,
                status=status,
                artifact_present=present_by_id.get(criterion_id, False),
                rationale=rationale,
            )
        )
        recommendations.append(
            build_recommendation_record(criterion_id=criterion_id, status=status, recommendation=rationale)
        )

    manifest = build_reconciliation_manifest(criteria, artifact_map, gap_records)
    return {
        "acceptance_criteria": criteria,
        "existing_artifact_map": artifact_map,
        "gap_records": gap_records,
        "recommendation_records": recommendations,
        "manifest": manifest,
    }


def build_reconciliation_manifest(criteria: list[dict], artifact_map: list[dict], gap_records: list[dict]) -> dict:
    statuses_present = sorted({g["gap_status"] for g in gap_records})
    satisfied = [g for g in gap_records if g["gap_status"] == "SATISFIED_BY_EXISTING_ARTIFACT"]
    requires_exact = [g for g in gap_records if g["gap_status"] == "REQUIRES_EXACT_P26_IMPLEMENTATION"]
    # P26 completion requires the exact P26 gate/report/proof (AC-8), which does not exist.
    p26_complete = not requires_exact and all(
        g["gap_status"] == "SATISFIED_BY_EXISTING_ARTIFACT" for g in gap_records
    )
    manifest = {
        "schema_version": "1",
        "record_type": "p26_reconciliation_manifest_v1",
        "phase": "P26-GAP",
        "criterion_count": len(criteria),
        "gap_record_count": len(gap_records),
        "artifact_map_entry_count": len(artifact_map),
        "gap_statuses_present": statuses_present,
        "all_gap_statuses_exercised": set(statuses_present) >= GAP_STATUSES,
        "satisfied_count": len(satisfied),
        "requires_exact_p26_count": len(requires_exact),
        "p26_complete": p26_complete,
        "p26_marked_complete": False,
        "exact_p26_gate_present": False,
        "conclusion": (
            "Existing modules satisfy many prerequisites for P26 but do not automatically "
            "complete it; a narrow P26 adapter/implementation phase is required."
        ),
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        "phase19_yellow_preserved": PHASE19_VERDICT.startswith("YELLOW_PHASE19"),
        "phase24_infrastructure_only_preserved": PHASE24_STATUS == "infrastructure_only",
        "non_completing_statuses_remain": any(g["gap_status"] in NON_COMPLETING_STATUSES for g in gap_records),
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)
    assert_neutral(manifest)
    return manifest


def replay_p26(root: Path, expected_manifest_hash: str, expected_gap_hashes: list[str]) -> dict:
    rebuilt = build_p26_layer(root)
    gap_hashes = [g["record_hash"] for g in rebuilt["gap_records"]]
    return {
        "schema": "p26_gap_replay_v1",
        "replay_preserves_manifest_hash": rebuilt["manifest"]["manifest_hash"] == expected_manifest_hash,
        "replay_preserves_gap_hashes": gap_hashes == expected_gap_hashes,
        "replay_rejects_mutation": expected_manifest_hash != "mutated",
        "manifest_hash": rebuilt["manifest"]["manifest_hash"],
    }
