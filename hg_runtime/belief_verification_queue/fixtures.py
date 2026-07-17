"""Deterministic WMBR-02 fixtures.

The fixture matrix bundle reuses the WMBR-01A deterministic fixtures, which
already contain unsourced consensus, factual divergence, refusal divergence,
omission divergence, moral conflict, and framing divergence. Two laundering
fixtures probe that the gate rejects truth/tool-authorization laundering.
"""

from __future__ import annotations

from hg_runtime.cross_model_perspective.artifact_writer import build_artifacts as _build_matrix_artifacts
from hg_runtime.cross_model_perspective.fixtures import fixture_prompts, fixture_receipts


def fixture_matrix_bundle() -> dict:
    """Build an in-memory WMBR-01A-shaped matrix bundle from fixtures."""
    meta = {p["prompt_id"]: p for p in fixture_prompts()}
    artifacts = _build_matrix_artifacts(fixture_receipts(), meta)
    return {
        "source_bundle": "FIXTURE_WMBR01A_MATRIX",
        "perspective_matrix": artifacts["perspective_matrix"],
        "divergence_matrix": artifacts["divergence_matrix"],
        "omission_patterns": artifacts["omission_patterns"],
        "refusal_patterns": artifacts["refusal_patterns"],
        "framing_signatures": artifacts["framing_signatures"],
        "moral_conflict_records": artifacts["moral_conflict_records"],
        "evidence_gap_tasks": artifacts["evidence_gap_tasks"],
        "summary": artifacts["summary"],
    }


def truth_laundering_attempt() -> dict:
    """A claim record that illegally marks consensus as true (must be rejected)."""
    return {
        "schema": "candidate_claim_record_v1",
        "claim_id": "claim-laundered-true",
        "truth_status": "VERIFIED_TRUE",
        "belief_status": "PROMOTED",
        "claim_marked_true": True,
        "belief_promoted": True,
    }


def tool_authorization_laundering_attempt() -> dict:
    """A verification task that illegally authorizes an external tool (must be rejected)."""
    return {
        "schema": "verification_task_v1",
        "task_id": "vtask-laundered-tool",
        "task_status": "AUTHORIZED",
        "tool_authorized": True,
        "external_call_authorized": True,
    }
