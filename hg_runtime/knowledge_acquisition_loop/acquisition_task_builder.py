"""P30-1 acquisition task builder — builds acquisition tasks from P29 workbench gaps and evidence gaps."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.knowledge_acquisition_loop.acquisition_candidate import build_acquisition_candidate
from hg_runtime.knowledge_acquisition_loop.acquisition_source import build_acquisition_source_record
from hg_runtime.knowledge_acquisition_loop.acquisition_task import build_acquisition_task
from hg_runtime.knowledge_acquisition_loop.hashing import with_hash
from hg_runtime.knowledge_acquisition_loop.knowledge_policy import build_knowledge_acquisition_policy
from hg_runtime.knowledge_acquisition_loop.schemas import (
    PHASE19_VERDICT,
    PHASE24_STATUS,
    P30_INVARIANTS,
    assert_neutral,
    neutral_flags,
)
from hg_runtime.knowledge_acquisition_loop.workbench_gap_mapper import (
    map_evidence_gaps_to_candidates,
    map_workbench_gaps_to_candidates,
)


def _task_type_for_source(source_type: str) -> str:
    return {
        "local_proof": "read_local_proof",
        "local_evidence": "read_local_evidence",
        "local_report": "read_local_report",
        "local_artifact": "read_local_artifact",
    }.get(source_type, "read_local_artifact")


def build_acquisition_task_layer(repo_root: Path) -> dict:
    policy = build_knowledge_acquisition_policy()
    gap_result = map_workbench_gaps_to_candidates(repo_root)
    evidence_candidates = map_evidence_gaps_to_candidates(repo_root)
    raw_candidates = gap_result["workbench_gap_candidates"] + evidence_candidates

    candidates = []
    sources = []
    tasks = []

    for raw in raw_candidates:
        candidate = build_acquisition_candidate(
            candidate_id=raw["candidate_id"],
            description=raw["description"],
            source_type=raw["source_type"],
            provenance_refs=[raw.get("proof_ref", raw.get("origin", "unknown"))],
        )
        candidates.append(candidate)

        source = build_acquisition_source_record(
            source_id=f"src-{raw['candidate_id']}",
            source_type=raw["source_type"],
            artifact_path=raw.get("proof_ref", raw.get("origin", "unknown")),
            provenance_refs=[raw.get("proof_ref", raw.get("origin", "unknown"))],
            quality_score="fixture_verified",
        )
        sources.append(source)

        task = build_acquisition_task(
            task_id=f"task-{raw['candidate_id']}",
            task_type=_task_type_for_source(raw["source_type"]),
            candidate_id=candidate["candidate_id"],
            description=f"Acquire: {raw['description']}",
            source_refs=[source["source_id"]],
            fixture_only=True,
            sandbox_only=True,
        )
        tasks.append(task)

    all_fixture_only = all(t["fixture_only"] for t in tasks) if tasks else True
    all_sandbox_only = all(t["sandbox_only"] for t in tasks) if tasks else True

    manifest = {
        "record_type": "knowledge_acquisition_task_manifest_v1",
        "schema_version": "1",
        "manifest_id": "p30-1-acquisition-task-manifest",
        "repo_root": str(repo_root),
        "candidate_count": len(candidates),
        "source_count": len(sources),
        "task_count": len(tasks),
        "all_fixture_only": all_fixture_only,
        "all_sandbox_only": all_sandbox_only,
        "invariants": P30_INVARIANTS,
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        "acquired_claim_treated_as_truth": False,
        "acquisition_result_treated_as_belief": False,
        "belief_promotion_automatic": False,
    }
    with_hash(manifest, "manifest_hash")
    assert_neutral(manifest)

    return {
        "policy": policy,
        "candidates": candidates,
        "sources": sources,
        "tasks": tasks,
        "manifest": manifest,
    }


def replay_acquisition_task_layer(repo_root: Path, expected_manifest_hash: str) -> dict:
    layer = build_acquisition_task_layer(repo_root)
    return {
        "replay_preserves_manifest_hash": layer["manifest"]["manifest_hash"] == expected_manifest_hash,
        "replayed_manifest_hash": layer["manifest"]["manifest_hash"],
        "expected_manifest_hash": expected_manifest_hash,
    }
