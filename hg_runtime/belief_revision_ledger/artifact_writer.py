"""Proof artifact writers and the WMBR-03 orchestrator."""

from __future__ import annotations

import json
import re
from pathlib import Path

from hg_runtime.belief_revision_ledger.belief_state import unverified_state
from hg_runtime.belief_revision_ledger.queue_loader import validate_queue_bundle
from hg_runtime.belief_revision_ledger.replay import replay_ledger
from hg_runtime.belief_revision_ledger.revision_engine import process_claim_evidence
from hg_runtime.belief_revision_ledger.schemas import (
    BELIEF_PROVISIONALLY_SUPPORTED,
    BELIEF_REVISION_IS_NOT_CERTAINTY,
    BELIEF_STATE_IS_NOT_TRUTH,
    BELIEF_UNVERIFIED,
    CONTRADICTION_CREATES_PATH,
    EVIDENCE_MUST_CARRY_PROVENANCE,
    MANIFEST_SCHEMA,
    MODEL_OUTPUT_IS_NOT_EVIDENCE,
    NO_PROVENANCE_NO_PROMOTION,
    PROMOTED_STATUSES,
    SOURCE_PHASE_ID,
    VERIFICATION_TASK_IS_NOT_EVIDENCE,
    assert_neutral,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash

SECRET_RE = re.compile(r"sk-lm-[A-Za-z0-9:_-]{12,}|sk-[A-Za-z0-9]{24,}|Authorization\s*:\s*Bearer\s+\S+|Bearer\s+[A-Za-z0-9_-]{20,}", re.I)

# Deterministic scenario assignment by target position.
SCENARIO_STANCES = {
    0: ["SUPPORTS"],
    1: ["CONTRADICTS"],
    2: ["INSUFFICIENT"],
    3: ["SUPPORTS", "CONTRADICTS"],
}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


def _source_matrix_ids(bundle: dict) -> list[str]:
    ids = {c.get("source_matrix_id") for c in bundle.get("belief_conflicts", [])}
    return sorted(i for i in ids if i)


def build_ledger(bundle: dict) -> dict:
    """Run the belief-revision pipeline over a WMBR-02 queue bundle."""
    validate_queue_bundle(bundle)
    claims_by_id = {c["claim_id"]: c for c in bundle["candidate_claims"]}
    tasks = sorted(bundle["verification_tasks"], key=lambda t: t.get("task_id", ""))
    matrix_ids = _source_matrix_ids(bundle)

    # Pick deterministic distinct target claims, one per task (first available claim).
    targets: list[tuple[str, dict]] = []
    used: set[str] = set()
    for task in tasks:
        for claim_id in task.get("source_claim_ids", []):
            if claim_id in claims_by_id and claim_id not in used:
                used.add(claim_id)
                targets.append((claim_id, task))
                break

    evidence_receipts: list[dict] = []
    belief_states: list[dict] = []
    revisions: list[dict] = []
    contradictions: list[dict] = []
    retractions: list[dict] = []
    provenance_chains: list[dict] = []

    for i, (claim_id, task) in enumerate(targets):
        stances = SCENARIO_STANCES[i % 4]
        result = process_claim_evidence(claims_by_id[claim_id], task, stances, matrix_ids)
        evidence_receipts.extend(result["evidence_receipts"])
        revisions.extend(result["revisions"])
        contradictions.extend(result["contradictions"])
        retractions.extend(result["retractions"])
        belief_states.append(result["belief_state"])
        provenance_chains.append(result["provenance_chain"])

    # Untargeted claims remain UNVERIFIED.
    for claim_id, claim in claims_by_id.items():
        if claim_id not in used:
            belief_states.append(unverified_state(claim_id, claim.get("claim_hash", "")))

    belief_states.sort(key=lambda s: s["belief_state_id"])
    revisions.sort(key=lambda r: r["revision_id"])
    evidence_receipts.sort(key=lambda r: r["evidence_receipt_id"])
    contradictions.sort(key=lambda c: c["contradiction_id"])
    retractions.sort(key=lambda r: r["retraction_id"])
    provenance_chains.sort(key=lambda p: p["provenance_chain_id"])

    all_evidence_has_provenance = all(
        r.get("provenance_uri_or_fixture_id") and r.get("provenance_kind") for r in evidence_receipts
    )
    promoted_states = [s for s in belief_states if s["belief_status"] in PROMOTED_STATUSES]
    provenance_for_promoted = all(s.get("provenance_chain_hash") for s in promoted_states)
    supporting_only_provisional = all(
        s["belief_status"] != "VERIFIED_TRUE" and s["belief_status"] != "TRUE"
        for s in belief_states
    )
    unsupported_remain_unverified = any(s["belief_status"] == BELIEF_UNVERIFIED for s in belief_states)

    manifest = {
        "schema": MANIFEST_SCHEMA,
        "ledger_id": "wmbr03-belief-revision-ledger",
        "source_phase": SOURCE_PHASE_ID,
        "source_proof_bundle": bundle.get("source_bundle", "UNKNOWN"),
        "claim_count": len(claims_by_id),
        "belief_state_count": len(belief_states),
        "evidence_receipt_count": len(evidence_receipts),
        "revision_count": len(revisions),
        "contradiction_count": len(contradictions),
        "retraction_count": len(retractions),
        "provenance_chain_count": len(provenance_chains),
        "revision_hashes": [r["revision_hash"] for r in revisions],
        "all_evidence_has_provenance": all_evidence_has_provenance,
        "provenance_chain_required_for_promoted_state": provenance_for_promoted,
        "supporting_evidence_only_provisional": supporting_only_provisional,
        "unsupported_claims_remain_unverified": unsupported_remain_unverified,
        **neutral_flags(),
    }
    manifest["manifest_hash"] = canonical_hash(manifest)

    replay = replay_ledger(revisions, belief_states, evidence_receipts, manifest)

    status_counts: dict[str, int] = {}
    for s in belief_states:
        status_counts[s["belief_status"]] = status_counts.get(s["belief_status"], 0) + 1

    summary = {
        "doctrine": "Every model is a compressed civilization artifact.",
        "claim_count": len(claims_by_id),
        "belief_state_count": len(belief_states),
        "evidence_receipt_count": len(evidence_receipts),
        "revision_count": len(revisions),
        "contradiction_count": len(contradictions),
        "retraction_count": len(retractions),
        "provenance_chain_count": len(provenance_chains),
        "belief_status_counts": status_counts,
        "all_evidence_has_provenance": all_evidence_has_provenance,
        "supporting_evidence_only_provisional": supporting_only_provisional,
        "unsupported_claims_remain_unverified": unsupported_remain_unverified,
        "replay_preserves_revision_hashes": replay["replay_preserves_revision_hashes"],
        "boundaries": {
            "model_output_is_not_evidence": MODEL_OUTPUT_IS_NOT_EVIDENCE,
            "verification_task_is_not_evidence": VERIFICATION_TASK_IS_NOT_EVIDENCE,
            "belief_state_is_not_truth": BELIEF_STATE_IS_NOT_TRUTH,
            "belief_revision_is_not_certainty": BELIEF_REVISION_IS_NOT_CERTAINTY,
            "evidence_must_carry_provenance": EVIDENCE_MUST_CARRY_PROVENANCE,
            "no_provenance_no_promotion": NO_PROVENANCE_NO_PROMOTION,
            "contradiction_creates_path": CONTRADICTION_CREATES_PATH,
        },
    }
    summary["summary_hash"] = canonical_hash(summary)

    out = {
        "evidence_receipts": evidence_receipts,
        "belief_states": belief_states,
        "revisions": revisions,
        "contradictions": contradictions,
        "retractions": retractions,
        "provenance_chains": provenance_chains,
        "manifest": manifest,
        "replay": replay,
        "summary": summary,
    }

    # Defensive: refuse to emit any artifact that asserts a forbidden flag.
    for group in ("evidence_receipts", "belief_states", "revisions", "contradictions", "retractions", "provenance_chains"):
        for rec in out[group]:
            assert_neutral(rec)
    assert_neutral(manifest)
    return out


def secret_scan(out: dict) -> bool:
    text = json.dumps(out, sort_keys=True, default=str)
    return SECRET_RE.search(text) is None
