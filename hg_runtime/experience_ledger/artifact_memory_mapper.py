"""Map explicit local artifacts into P26 experience and memory records."""

from __future__ import annotations

from hg_runtime.experience_ledger.experience_record import build_experience_record
from hg_runtime.experience_ledger.hashing import with_hash
from hg_runtime.experience_ledger.memory_record import build_memory_record
from hg_runtime.experience_ledger.schemas import assert_neutral


EXPLICIT_ARTIFACT_MANIFEST = [
    {
        "artifact_id": "artifact-sle-rc",
        "family": "SLE-RC",
        "artifact_ref": "docs/proofs/autonomous_agent_zero/SLE-SAFE-LOCAL-EVIDENCE-RELEASE-CANDIDATE/20260620T220533Z",
        "verdict": "GREEN_SLE_SAFE_LOCAL_EVIDENCE_RELEASE_CANDIDATE",
        "boundary_tags": ["release_candidate_not_deployment", "evidence_not_truth", "phase19_yellow"],
        "provenance_refs": ["rc_artifact_index.json", "rc_boundary_matrix.json"],
        "source_quality_refs": ["SQP-SOURCE-QUALITY-PROVENANCE-CONSOLIDATION"],
    },
    {
        "artifact_id": "artifact-phase25",
        "family": "PHASE-25",
        "artifact_ref": "docs/proofs/autonomous_agent_zero/PHASE-25-ADVISORY-SELF-IMPROVEMENT/20260620T233108Z",
        "verdict": "GREEN_PHASE25_ADVISORY_SELF_IMPROVEMENT",
        "boundary_tags": ["advisory_not_patch_permission", "no_self_authorization", "operator_review_required"],
        "provenance_refs": ["proposal_records.jsonl", "refusal_records.jsonl"],
        "source_quality_refs": ["SAFE-LOCAL-EVIDENCE-ALPHA"],
    },
    {
        "artifact_id": "artifact-p26-gap",
        "family": "P26-GAP",
        "artifact_ref": "docs/proofs/autonomous_agent_zero/P26-EXPERIENCE-LEDGER-GAP-RECONCILIATION/20260620T233645Z",
        "verdict": "GREEN_P26_EXPERIENCE_LEDGER_GAP_RECONCILIATION",
        "boundary_tags": ["gap_analysis_not_completion", "p26_not_complete", "requires_exact_p26"],
        "provenance_refs": ["p26_gap_records.jsonl", "p26_acceptance_criteria_map.json"],
        "source_quality_refs": ["SLE-RC"],
    },
]


def build_artifact_manifest() -> dict:
    manifest = {
        "record_type": "p26_explicit_artifact_manifest_v1",
        "schema_version": "1",
        "manifest_id": "p26-1-explicit-artifact-manifest",
        "explicit_manifest_only": True,
        "artifact_count": len(EXPLICIT_ARTIFACT_MANIFEST),
        "artifacts": EXPLICIT_ARTIFACT_MANIFEST,
        "arbitrary_file_ingestion_enabled": False,
        "web_browse_performed": False,
        "external_provider_calls_made": False,
    }
    with_hash(manifest, "manifest_hash")
    assert_neutral(manifest)
    return manifest


def map_artifacts_to_memory() -> dict:
    experiences = []
    memories = []
    mapping = []
    for artifact in EXPLICIT_ARTIFACT_MANIFEST:
        experience = build_experience_record(
            experience_id=f"exp-{artifact['artifact_id']}",
            family=artifact["family"],
            artifact_ref=artifact["artifact_ref"],
            verdict=artifact["verdict"],
            boundary_tags=artifact["boundary_tags"],
            provenance_refs=artifact["provenance_refs"],
        )
        memory = build_memory_record(
            memory_id=f"mem-{artifact['artifact_id']}",
            experience_record=experience,
            provenance_refs=artifact["provenance_refs"],
            source_quality_refs=artifact["source_quality_refs"],
        )
        map_record = {
            "record_type": "artifact_memory_map_v1",
            "schema_version": "1",
            "artifact_id": artifact["artifact_id"],
            "experience_id": experience["experience_id"],
            "experience_hash": experience["experience_hash"],
            "memory_id": memory["memory_id"],
            "memory_hash": memory["memory_hash"],
            "belief_promoted": False,
            "authority_granted": False,
        }
        with_hash(map_record, "record_hash")
        assert_neutral(map_record)
        experiences.append(experience)
        memories.append(memory)
        mapping.append(map_record)
    return {"experience_records": experiences, "memory_records": memories, "artifact_memory_map": mapping}

