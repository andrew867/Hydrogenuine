"""Proof artifact writers and the WMBR-01A analysis orchestrator."""

from __future__ import annotations

import json
import re
from pathlib import Path

from hg_runtime.cross_model_perspective.divergence_matrix import build_divergence_matrix
from hg_runtime.cross_model_perspective.evidence_gap_generator import generate_evidence_gap_tasks
from hg_runtime.cross_model_perspective.framing_analyzer import analyze_framing
from hg_runtime.cross_model_perspective.moral_principle_extractor import (
    build_moral_consensus_matrix,
    extract_moral_conflicts,
)
from hg_runtime.cross_model_perspective.omission_detector import detect_omissions
from hg_runtime.cross_model_perspective.perspective_matrix import build_perspective_matrix
from hg_runtime.cross_model_perspective.receipt_loader import normalize_receipts
from hg_runtime.cross_model_perspective.refusal_analyzer import analyze_refusals
from hg_runtime.cross_model_perspective.replay import replay_matrices
from hg_runtime.cross_model_perspective.schemas import (
    CONSENSUS_IS_NOT_TRUTH,
    DISAGREEMENT_IS_NOT_EVIDENCE,
    DOCTRINE,
    EVIDENCE_GAP_TASK_IS_NOT_ACTION,
    FRAMING_IS_DESCRIPTIVE,
    MORAL_CONSENSUS_IS_NOT_AUTHORITY,
    OMISSION_IS_NOT_PROOF,
    PROVIDER_MODE,
    REFUSAL_IS_NOT_AUTHORITY,
    SUMMARY_SCHEMA,
    WILLINGNESS_IS_NOT_PERMISSION,
    assert_neutral,
    neutral_flags,
)
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


def build_artifacts(raw_receipts: list[dict], prompts_meta: dict[str, dict]) -> dict:
    """Run the full epistemic-spectroscopy pipeline over input receipts."""
    receipts = normalize_receipts(raw_receipts)
    perspective = build_perspective_matrix(receipts)
    divergence = build_divergence_matrix(receipts)
    omissions = detect_omissions(receipts, prompts_meta)
    refusals = analyze_refusals(receipts)
    framing = analyze_framing(receipts)
    moral_matrix = build_moral_consensus_matrix(receipts)
    moral_conflicts = extract_moral_conflicts(receipts)
    evidence_gap_tasks = generate_evidence_gap_tasks(receipts)
    replay = replay_matrices(perspective, divergence)

    summary = {
        "schema": SUMMARY_SCHEMA,
        "version": "cross_model_perspective_summary_v1",
        "doctrine": DOCTRINE,
        "provider_mode": PROVIDER_MODE,
        "receipt_count": len(receipts),
        "participant_count": len({r["participant_id"] for r in receipts}),
        "prompt_count": len({r["prompt_id"] for r in receipts}),
        "perspective_cell_count": perspective["cell_count"],
        "divergence_record_count": divergence["record_count"],
        "omission_pattern_count": len(omissions),
        "refusal_pattern_count": len(refusals),
        "framing_signature_count": len(framing),
        "moral_principle_count": moral_matrix["principle_count"],
        "moral_conflict_count": len(moral_conflicts),
        "evidence_gap_task_count": len(evidence_gap_tasks),
        "every_matrix_cell_links_to_receipt": perspective["every_cell_links_to_receipt"],
        "replay_preserves_matrix_hashes": replay["replay_preserves_matrix_hashes"],
        "boundaries": {
            "consensus_is_not_truth": CONSENSUS_IS_NOT_TRUTH,
            "disagreement_is_not_evidence": DISAGREEMENT_IS_NOT_EVIDENCE,
            "refusal_is_not_authority": REFUSAL_IS_NOT_AUTHORITY,
            "willingness_is_not_permission": WILLINGNESS_IS_NOT_PERMISSION,
            "moral_consensus_is_not_authority": MORAL_CONSENSUS_IS_NOT_AUTHORITY,
            "omission_is_not_proof_of_intent": OMISSION_IS_NOT_PROOF,
            "framing_signature_is_descriptive_only": FRAMING_IS_DESCRIPTIVE,
            "evidence_gap_tasks_are_not_actions": EVIDENCE_GAP_TASK_IS_NOT_ACTION,
        },
        **neutral_flags(),
    }
    summary["summary_hash"] = canonical_hash(summary)

    bundle = {
        "receipts": receipts,
        "perspective_matrix": perspective,
        "divergence_matrix": divergence,
        "omission_patterns": omissions,
        "refusal_patterns": refusals,
        "framing_signatures": framing,
        "moral_consensus_matrix": moral_matrix,
        "moral_conflict_records": moral_conflicts,
        "evidence_gap_tasks": evidence_gap_tasks,
        "replay": replay,
        "summary": summary,
    }
    # Defensive: refuse to emit any artifact that asserts a forbidden flag.
    assert_neutral(perspective)
    assert_neutral(divergence)
    assert_neutral(summary)
    for task in evidence_gap_tasks:
        assert_neutral(task)
    return bundle


def secret_scan(bundle: dict) -> bool:
    """Return True when no secret material is present in the artifacts."""
    text = json.dumps(bundle, sort_keys=True, default=str)
    return SECRET_RE.search(text) is None
