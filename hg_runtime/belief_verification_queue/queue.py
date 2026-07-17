"""Deterministic verification queue manifest."""

from __future__ import annotations

from hg_runtime.belief_verification_queue.schemas import (
    SOURCE_PHASE_ID,
    VERIFICATION_QUEUE_MANIFEST_SCHEMA,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def build_queue_manifest(source_proof_bundle: str, claims: list[dict], conflicts: list[dict], tasks: list[dict]) -> dict:
    manifest = {
        "schema": VERIFICATION_QUEUE_MANIFEST_SCHEMA,
        "queue_id": "wmbr02-verification-queue",
        "source_phase": SOURCE_PHASE_ID,
        "source_proof_bundle": source_proof_bundle,
        "task_count": len(tasks),
        "conflict_count": len(conflicts),
        "claim_count": len(claims),
        "task_ids": [t["task_id"] for t in tasks],
        "task_hashes": [t["task_hash"] for t in tasks],
        "all_tasks_unauthorized": all(
            not t["tool_authorized"] and not t["action_authorized"] and not t["external_call_authorized"]
            for t in tasks
        ),
        "all_claims_unverified": all(c["truth_status"] == "UNVERIFIED" for c in claims),
        "all_belief_status_not_promoted": all(c["belief_status"] == "NOT_PROMOTED" for c in claims),
        "external_calls_made": False,
        **neutral_flags(),
    }
    manifest["queue_hash"] = canonical_hash(manifest)
    return manifest
