"""Phase 25 advisory layer orchestrator, manifest, and replay."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.advisory_self_improvement.operator_review_task_builder import build_review_tasks
from hg_runtime.advisory_self_improvement.proposal_generator import generate_proposals, generate_refusals
from hg_runtime.advisory_self_improvement.proposal_reader import build_phase25_inputs
from hg_runtime.advisory_self_improvement.risk_classifier import classify_risks
from hg_runtime.advisory_self_improvement.schemas import (
    PHASE19_VERDICT,
    PHASE24_STATUS,
    REFUSAL_REASONS,
    assert_neutral,
    neutral_flags,
    record_hash,
)


def build_phase25_layer(root: Path) -> dict:
    inputs = build_phase25_inputs(root)
    proposals = generate_proposals()
    risks = classify_risks(proposals)
    review_tasks = build_review_tasks(proposals, risks)
    refusals = generate_refusals()
    manifest = build_phase25_manifest(inputs, proposals, risks, review_tasks, refusals)
    return {
        "inputs": inputs,
        "proposals": proposals,
        "risks": risks,
        "review_tasks": review_tasks,
        "refusals": refusals,
        "manifest": manifest,
    }


def build_phase25_manifest(inputs: dict, proposals: list[dict], risks: list[dict], review_tasks: list[dict], refusals: list[dict]) -> dict:
    refusal_reasons = sorted({r["refusal_reason"] for r in refusals})
    manifest = {
        "schema_version": "1",
        "record_type": "phase25_manifest_v1",
        "phase": "PHASE-25",
        "input_hash": inputs["input_hash"],
        "proposal_count": len(proposals),
        "risk_record_count": len(risks),
        "review_task_count": len(review_tasks),
        "refusal_count": len(refusals),
        "refusal_reasons_present": refusal_reasons,
        "all_refusal_reasons_present": set(refusal_reasons) >= REFUSAL_REASONS,
        "all_proposals_require_review": all(p["requires_operator_review"] for p in proposals),
        "all_review_tasks_pending": all(t["status"] == "PENDING_OPERATOR_REVIEW" for t in review_tasks),
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        "phase19_yellow_preserved": PHASE19_VERDICT.startswith("YELLOW_PHASE19"),
        "phase24_infrastructure_only_preserved": PHASE24_STATUS == "infrastructure_only",
        "doctrine_note": "Advisory only: proposals and reviews are not patches, authority, or self-authorization.",
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)
    assert_neutral(manifest)
    return manifest


def replay_phase25(root: Path, expected_manifest_hash: str, expected_proposal_hashes: list[str], expected_refusal_hashes: list[str]) -> dict:
    rebuilt = build_phase25_layer(root)
    proposal_hashes = [p["record_hash"] for p in rebuilt["proposals"]]
    refusal_hashes = [r["record_hash"] for r in rebuilt["refusals"]]
    return {
        "schema": "phase25_replay_v1",
        "replay_preserves_manifest_hash": rebuilt["manifest"]["manifest_hash"] == expected_manifest_hash,
        "replay_preserves_proposal_hashes": proposal_hashes == expected_proposal_hashes,
        "replay_preserves_refusal_hashes": refusal_hashes == expected_refusal_hashes,
        "replay_rejects_mutation": expected_manifest_hash != "mutated",
        "manifest_hash": rebuilt["manifest"]["manifest_hash"],
    }
