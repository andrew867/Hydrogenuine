"""Proof artifact writers and the WMBR-02 orchestrator."""

from __future__ import annotations

import json
import re
from pathlib import Path

from hg_runtime.belief_verification_queue.claim_extractor import extract_candidate_claims
from hg_runtime.belief_verification_queue.conflict_detector import detect_conflicts
from hg_runtime.belief_verification_queue.evidence_policy import build_evidence_policy_receipts
from hg_runtime.belief_verification_queue.matrix_loader import validate_matrix_bundle
from hg_runtime.belief_verification_queue.priority import build_priority_record
from hg_runtime.belief_verification_queue.queue import build_queue_manifest
from hg_runtime.belief_verification_queue.replay import replay_queue
from hg_runtime.belief_verification_queue.schemas import (
    CONFLICT_IS_NOT_EVIDENCE,
    CONSENSUS_IS_NOT_TRUTH,
    DIVERGENCE_IS_NOT_EVIDENCE,
    MORAL_CONSENSUS_IS_NOT_AUTHORITY,
    REFUSAL_IS_NOT_AUTHORITY,
    SOURCE_REQUEST_IS_NOT_TOOL_AUTH,
    SPECTROSCOPY_IS_NOT_BELIEF,
    TASK_IS_NOT_ACTION,
    WILLINGNESS_IS_NOT_PERMISSION,
    assert_neutral,
)
from hg_runtime.belief_verification_queue.verification_task import build_verification_tasks
from hg_runtime.memory_ledger.hash_chain import canonical_hash

SECRET_RE = re.compile(r"sk-lm-[A-Za-z0-9:_-]{12,}|sk-[A-Za-z0-9]{24,}|Authorization\s*:\s*Bearer\s+\S+|Bearer\s+[A-Za-z0-9_-]{20,}", re.I)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


def build_queue(bundle: dict) -> dict:
    """Run the full belief-conflict / verification-queue pipeline over a matrix bundle."""
    validate_matrix_bundle(bundle)
    claims = extract_candidate_claims(bundle)
    conflicts = detect_conflicts(bundle)
    tasks = build_verification_tasks(conflicts, claims)
    priority_records = [build_priority_record(c) for c in conflicts]
    evidence_policies = build_evidence_policy_receipts([c["claim_kind"] for c in claims])
    manifest = build_queue_manifest(bundle.get("source_bundle", "UNKNOWN"), claims, conflicts, tasks)
    replay = replay_queue(tasks, manifest)

    summary = {
        "doctrine": SPECTROSCOPY_IS_NOT_BELIEF,
        "claim_count": len(claims),
        "conflict_count": len(conflicts),
        "verification_task_count": len(tasks),
        "evidence_policy_count": len(evidence_policies),
        "all_claims_unverified": manifest["all_claims_unverified"],
        "all_belief_status_not_promoted": manifest["all_belief_status_not_promoted"],
        "all_tasks_unauthorized": manifest["all_tasks_unauthorized"],
        "replay_preserves_queue_hash": replay["replay_preserves_queue_hash"],
        "boundaries": {
            "spectroscopy_is_not_belief": SPECTROSCOPY_IS_NOT_BELIEF,
            "conflict_is_not_evidence": CONFLICT_IS_NOT_EVIDENCE,
            "task_is_not_action": TASK_IS_NOT_ACTION,
            "source_request_is_not_tool_auth": SOURCE_REQUEST_IS_NOT_TOOL_AUTH,
            "consensus_is_not_truth": CONSENSUS_IS_NOT_TRUTH,
            "divergence_is_not_evidence": DIVERGENCE_IS_NOT_EVIDENCE,
            "refusal_is_not_authority": REFUSAL_IS_NOT_AUTHORITY,
            "willingness_is_not_permission": WILLINGNESS_IS_NOT_PERMISSION,
            "moral_consensus_is_not_authority": MORAL_CONSENSUS_IS_NOT_AUTHORITY,
        },
    }
    summary["summary_hash"] = canonical_hash(summary)

    out = {
        "claims": claims,
        "conflicts": conflicts,
        "verification_tasks": tasks,
        "priority_records": priority_records,
        "evidence_policies": evidence_policies,
        "queue_manifest": manifest,
        "replay": replay,
        "summary": summary,
    }
    # Defensive: refuse to emit any artifact that asserts a forbidden flag.
    for claim in claims:
        assert_neutral(claim)
    for conflict in conflicts:
        assert_neutral(conflict)
    for task in tasks:
        assert_neutral(task)
    assert_neutral(manifest)
    return out


def secret_scan(out: dict) -> bool:
    text = json.dumps(out, sort_keys=True, default=str)
    return SECRET_RE.search(text) is None
