"""Deterministic WMBR-03 fixtures.

The fixture queue bundle reuses the WMBR-02 deterministic pipeline (itself built
on WMBR-01A fixtures). Laundering / rejection fixtures probe that the engine and
gate refuse missing provenance, model-output-as-evidence,
verification-task-as-evidence, truth/certainty laundering, and claim rewrite.
"""

from __future__ import annotations

from hg_runtime.belief_verification_queue.artifact_writer import build_queue
from hg_runtime.belief_verification_queue.fixtures import fixture_matrix_bundle


def fixture_queue_bundle() -> dict:
    """Build an in-memory WMBR-02-shaped queue bundle from fixtures."""
    queue = build_queue(fixture_matrix_bundle())
    return {
        "source_bundle": "FIXTURE_WMBR02_QUEUE",
        "candidate_claims": queue["claims"],
        "verification_tasks": queue["verification_tasks"],
        "belief_conflicts": queue["conflicts"],
        "evidence_policy_receipts": queue["evidence_policies"],
        "queue_manifest": queue["queue_manifest"],
        "summary": {"verdict": "GREEN_WMBR_02_BELIEF_CONFLICT_VERIFICATION_QUEUE"},
    }


def supporting_evidence_fixture() -> dict:
    return {"stance": "SUPPORTS", "expected_status": "PROVISIONALLY_SUPPORTED"}


def contradicting_evidence_fixture() -> dict:
    return {"stance": "CONTRADICTS", "expected_status": "CONTRADICTED"}


def insufficient_evidence_fixture() -> dict:
    return {"stance": "INSUFFICIENT", "expected_status": "INSUFFICIENT_EVIDENCE"}


def retraction_fixture() -> dict:
    return {"stances": ["SUPPORTS", "CONTRADICTS"], "expected_status": "RETRACTED"}


def missing_provenance_fixture() -> dict:
    """Evidence receipt with no provenance (must be rejected)."""
    return {
        "schema": "evidence_receipt_v1",
        "evidence_receipt_id": "ev-missing-provenance",
        "evidence_kind": "SYNTHETIC_PRIMARY_SOURCE",
        "provenance_uri_or_fixture_id": "",
        "provenance_kind": "",
        "model_output_is_evidence": False,
    }


def model_output_as_evidence_fixture() -> dict:
    """Evidence receipt that launders model output as evidence (must be rejected)."""
    return {
        "schema": "evidence_receipt_v1",
        "evidence_receipt_id": "ev-model-output",
        "evidence_kind": "SYNTHETIC_PRIMARY_SOURCE",
        "provenance_uri_or_fixture_id": "fixture-model-output",
        "provenance_kind": "FIXTURE",
        "model_output_is_evidence": True,
    }


def verification_task_as_evidence_fixture() -> dict:
    """Evidence receipt that launders a verification task as evidence (must be rejected)."""
    return {
        "schema": "evidence_receipt_v1",
        "evidence_receipt_id": "ev-task-as-evidence",
        "evidence_kind": "SYNTHETIC_PRIMARY_SOURCE",
        "provenance_uri_or_fixture_id": "fixture-task",
        "provenance_kind": "FIXTURE",
        "model_output_is_evidence": False,
        "verification_task_treated_as_evidence": True,
    }


def truth_laundering_fixture() -> dict:
    """Belief state that illegally claims truth (must be rejected by assert_neutral)."""
    return {
        "schema": "belief_state_record_v1",
        "belief_state_id": "belief-laundered-truth",
        "belief_status": "PROVISIONALLY_SUPPORTED",
        "truth_claimed": True,
    }


def certainty_laundering_fixture() -> dict:
    """Belief revision that illegally claims certainty (must be rejected)."""
    return {
        "schema": "belief_revision_record_v1",
        "revision_id": "rev-laundered-certainty",
        "certainty_claimed": True,
    }


def claim_rewrite_fixture() -> dict:
    """Retraction that illegally rewrites/deletes the original claim (must be rejected)."""
    return {
        "schema": "retraction_record_v1",
        "retraction_id": "retraction-laundered-rewrite",
        "original_claim_preserved": False,
        "deletion_performed": True,
        "rewrite_performed": True,
    }
