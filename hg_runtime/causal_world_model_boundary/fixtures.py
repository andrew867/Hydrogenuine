"""Deterministic WMBR-04 fixtures.

The fixture ledger bundle reuses the WMBR-03 deterministic pipeline (itself built
on WMBR-02 / WMBR-01A fixtures), which already yields provisionally-supported,
contradicted, insufficient, retracted, and unverified belief states. Laundering /
rejection fixtures probe that the engine and gate refuse causal-truth laundering,
correlation-as-causation, and intervention authorization.
"""

from __future__ import annotations

from hg_runtime.belief_revision_ledger.artifact_writer import build_ledger
from hg_runtime.belief_revision_ledger.fixtures import fixture_queue_bundle


def fixture_ledger_bundle() -> dict:
    """Build an in-memory WMBR-03-shaped belief revision ledger from fixtures."""
    ledger = build_ledger(fixture_queue_bundle())
    return {
        "source_bundle": "FIXTURE_WMBR03_LEDGER",
        "belief_states": ledger["belief_states"],
        "belief_revisions": ledger["revisions"],
        "evidence_receipts": ledger["evidence_receipts"],
        "contradiction_records": ledger["contradictions"],
        "retraction_records": ledger["retractions"],
        "provenance_chains": ledger["provenance_chains"],
        "manifest": ledger["manifest"],
        "summary": {"verdict": "GREEN_WMBR_03_BELIEF_REVISION_LEDGER"},
    }


def provisionally_supported_causal_fixture() -> dict:
    return {"belief_status": "PROVISIONALLY_SUPPORTED", "expected_hypothesis_status": "PROPOSED"}


def correlation_only_fixture() -> dict:
    return {"scenario": "CORRELATION", "expected_relation": "CORRELATES_WITH"}


def mechanism_proposal_fixture() -> dict:
    return {"scenario": "MECHANISM", "mechanism_is_proof": False}


def prediction_fixture() -> dict:
    return {"prediction_status": "UNTESTED", "prediction_is_verification": False}


def intervention_proposal_fixture() -> dict:
    return {"intervention_status": "PROPOSED_NOT_AUTHORIZED", "intervention_authorized": False}


def contradicted_belief_fixture() -> dict:
    return {"belief_status": "CONTRADICTED", "expected_hypothesis_status": "CONTRADICTED"}


def retracted_claim_fixture() -> dict:
    return {"belief_status": "RETRACTED", "expected_seeded": False}


def causal_truth_laundering_fixture() -> dict:
    """Hypothesis that illegally claims causal truth (must be rejected)."""
    return {
        "schema": "causal_hypothesis_record_v1",
        "hypothesis_id": "hyp-laundered-truth",
        "hypothesis_status": "PROPOSED",
        "causal_truth_claimed": True,
    }


def correlation_laundering_fixture() -> dict:
    """Edge that illegally treats correlation as causation (must be rejected)."""
    return {
        "schema": "causal_edge_record_v1",
        "edge_id": "edge-laundered-correlation",
        "relation_type": "CORRELATES_WITH",
        "correlation_is_causation": True,
    }


def intervention_authorization_laundering_fixture() -> dict:
    """Intervention that illegally authorizes a tool/action (must be rejected)."""
    return {
        "schema": "intervention_proposal_v1",
        "intervention_id": "intv-laundered-auth",
        "intervention_status": "PROPOSED_NOT_AUTHORIZED",
        "intervention_authorized": True,
        "action_authorized": True,
        "tools_authorized": True,
    }
