"""Assemble a rehydrated context packet from prior proof/audit data.

Everything loaded is advisory. Nothing grants authority, tool permission,
or external action permission.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from hg_runtime.memory_rehydration.proof_loader import load_proof_summary, load_jsonl
from hg_runtime.memory_rehydration.seed_progress import load_seed_progress_summary
from hg_runtime.memory_rehydration.evidence_gap_loader import load_evidence_gap_backlog
from hg_runtime.memory_rehydration.quality_memory import load_quality_summary
from hg_runtime.memory_rehydration.model_performance_memory import load_model_performance

SCHEMA_VERSION = "rehydrated_context_packet_v1"


def build_context_packet(source_run_id: str, proof_path: str, audit_path: str) -> dict:
    """Build a rehydrated context packet. All fields are advisory."""

    packet = {
        "schema": SCHEMA_VERSION,
        "source_run_id": source_run_id,
        "source_proof_path": proof_path,
        "loaded_at": datetime.now(timezone.utc).isoformat(),
        "seed_progress": None,
        "evidence_gaps": [],
        "quality_summary": None,
        "model_performance_summary": None,
        "operator_review_items": [],
        "second_pass_candidates": [],
        "stale_fields": [],
        "memory_treated_as_truth": False,
        "proof_treated_as_authority": False,
        "grants_tool_authority": False,
        "grants_external_action": False,
    }

    summary = load_seed_progress_summary(audit_path)
    if summary:
        packet["seed_progress"] = summary
    else:
        packet["stale_fields"].append("seed_progress")

    gaps = load_evidence_gap_backlog(audit_path)
    packet["evidence_gaps"] = gaps

    qsum = load_quality_summary(audit_path)
    packet["quality_summary"] = qsum

    mperf = load_model_performance(audit_path)
    packet["model_performance_summary"] = mperf

    review_items = load_jsonl(os.path.join(audit_path, "operator_review_backlog.jsonl"))
    packet["operator_review_items"] = review_items

    sp_vert = load_jsonl(os.path.join(audit_path, "second_pass_vertical_candidates.jsonl"))
    sp_horiz = load_jsonl(os.path.join(audit_path, "second_pass_horizontal_clusters.jsonl"))
    packet["second_pass_candidates"] = sp_vert + sp_horiz

    return packet


def validate_context_packet(packet: dict) -> list[str]:
    errors = []
    if packet.get("schema") != SCHEMA_VERSION:
        errors.append(f"wrong schema: {packet.get('schema')}")
    if packet.get("memory_treated_as_truth"):
        errors.append("memory_treated_as_truth must be False")
    if packet.get("proof_treated_as_authority"):
        errors.append("proof_treated_as_authority must be False")
    if packet.get("grants_tool_authority"):
        errors.append("grants_tool_authority must be False")
    if packet.get("grants_external_action"):
        errors.append("grants_external_action must be False")
    return errors
