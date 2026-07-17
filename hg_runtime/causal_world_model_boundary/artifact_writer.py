"""Proof artifact writers and the WMBR-04 orchestrator."""

from __future__ import annotations

import json
import re
from pathlib import Path

from hg_runtime.causal_world_model_boundary.belief_loader import validate_ledger_bundle
from hg_runtime.causal_world_model_boundary.causal_claim import build_causal_claim
from hg_runtime.causal_world_model_boundary.causal_hypothesis import build_causal_hypothesis
from hg_runtime.causal_world_model_boundary.correlation_detector import (
    assert_correlation_not_causation,
    build_causal_edge,
)
from hg_runtime.causal_world_model_boundary.falsification import build_falsification_condition
from hg_runtime.causal_world_model_boundary.intervention_boundary import (
    build_intervention_proposal,
    validate_intervention_proposal,
)
from hg_runtime.causal_world_model_boundary.mechanism_model import build_mechanism_proposal
from hg_runtime.causal_world_model_boundary.prediction import build_prediction_record
from hg_runtime.causal_world_model_boundary.provenance import (
    index_provenance_chains,
    is_provenance_bound,
    provenance_chain_ids_for,
)
from hg_runtime.causal_world_model_boundary.replay import replay_graph
from hg_runtime.causal_world_model_boundary.schemas import (
    BELIEF_STATE_IS_NOT_TRUTH,
    BELIEF_REVISION_IS_NOT_CERTAINTY,
    CAUSAL_HYPOTHESIS_IS_NOT_TRUTH,
    CONTRADICTION_STAYS_VISIBLE,
    CORRELATION_IS_NOT_CAUSATION,
    FALSIFICATION_IS_NOT_AUTHORITY,
    GRAPH_MANIFEST_SCHEMA,
    INTERVENTION_IS_NOT_ACTION,
    MECHANISM_IS_NOT_PROOF,
    PREDICTION_IS_NOT_VERIFICATION,
    SEED_BELIEF_STATUSES,
    SOURCE_PHASE_ID,
    assert_neutral,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash

SECRET_RE = re.compile(r"sk-lm-[A-Za-z0-9:_-]{12,}|sk-[A-Za-z0-9]{24,}|Authorization\s*:\s*Bearer\s+\S+|Bearer\s+[A-Za-z0-9_-]{20,}", re.I)

# Scenario cycle for PROPOSED (provisionally-supported) seeds.
SCENARIO_CYCLE = ("CAUSAL", "CORRELATION", "MECHANISM", "PREDICTION")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


def _scenario_language(scenario: str) -> tuple[bool, bool, bool]:
    """Return (causal, correlation, mechanism) language flags for a scenario."""
    if scenario == "CORRELATION":
        return False, True, False
    if scenario == "MECHANISM":
        return True, False, True
    return True, False, False


def build_causal_graph(bundle: dict) -> dict:
    """Run the causal-world-model-boundary pipeline over a WMBR-03 ledger bundle."""
    validate_ledger_bundle(bundle)
    provenance_index = index_provenance_chains(bundle.get("provenance_chains", []))
    belief_states = sorted(bundle["belief_states"], key=lambda s: s["belief_state_id"])

    causal_claims: list[dict] = []
    hypotheses: list[dict] = []
    edges: list[dict] = []
    mechanisms: list[dict] = []
    predictions: list[dict] = []
    interventions: list[dict] = []
    falsifications: list[dict] = []

    retracted_seeds_seen = 0
    proposed_index = 0

    for state in belief_states:
        status = state.get("belief_status")
        if status == "RETRACTED":
            retracted_seeds_seen += 1
            continue  # retracted claims do not seed active hypotheses
        if status not in SEED_BELIEF_STATUSES:
            continue  # UNVERIFIED / non-provenance-bound are not seeds
        if not is_provenance_bound(state, provenance_index):
            continue

        if status == "PROVISIONALLY_SUPPORTED":
            scenario = SCENARIO_CYCLE[proposed_index % len(SCENARIO_CYCLE)]
            proposed_index += 1
        else:
            scenario = "CAUSAL"  # contradicted / insufficient still get a visible edge

        causal_lang, corr_lang, mech_lang = _scenario_language(scenario)
        supporting = state.get("supporting_evidence_receipt_ids", [])
        contradicting = state.get("contradicting_evidence_receipt_ids", [])
        prov_ids = provenance_chain_ids_for(state, provenance_index)

        claim = build_causal_claim(
            belief_state=state,
            evidence_ids=[*supporting, *contradicting],
            causal_language=causal_lang,
            correlation_language=corr_lang,
            mechanism_language=mech_lang,
        )
        hypothesis = build_causal_hypothesis(
            causal_claim=claim,
            belief_state=state,
            provenance_chain_ids=prov_ids,
            supporting_ids=supporting,
            contradicting_ids=contradicting,
        )
        edge = build_causal_edge(hypothesis=hypothesis, scenario=scenario)
        assert_correlation_not_causation(edge)

        causal_claims.append(claim)
        hypotheses.append(hypothesis)
        edges.append(edge)

        # Mechanism / prediction / intervention / falsification only for active PROPOSED hypotheses.
        if hypothesis["hypothesis_status"] == "PROPOSED":
            falsifications.append(build_falsification_condition(hypothesis=hypothesis))
            if scenario in ("MECHANISM", "CAUSAL"):
                mechanisms.append(build_mechanism_proposal(hypothesis=hypothesis, evidence_ids=supporting))
            if scenario in ("PREDICTION", "CAUSAL", "CORRELATION"):
                predictions.append(build_prediction_record(hypothesis=hypothesis, status="UNTESTED"))
            if scenario == "CAUSAL":
                intervention = build_intervention_proposal(hypothesis=hypothesis)
                validate_intervention_proposal(intervention)
                interventions.append(intervention)

    # Deterministic ordering.
    causal_claims.sort(key=lambda c: c["causal_claim_id"])
    hypotheses.sort(key=lambda h: h["hypothesis_id"])
    edges.sort(key=lambda e: e["edge_id"])
    mechanisms.sort(key=lambda m: m["mechanism_id"])
    predictions.sort(key=lambda p: p["prediction_id"])
    interventions.sort(key=lambda i: i["intervention_id"])
    falsifications.sort(key=lambda f: f["condition_id"])

    nodes = {e["source_node_id"] for e in edges} | {e["target_node_id"] for e in edges}
    all_edges_hypothetical = all(
        e["edge_status"] in ("HYPOTHETICAL", "CONTRADICTED", "INSUFFICIENT_EVIDENCE") and not e["edge_is_truth"]
        for e in edges
    )
    all_hypotheses_provisional = all(not h["causal_truth_claimed"] and not h["certainty_claimed"] for h in hypotheses)
    no_interventions_authorized = all(
        not i["intervention_authorized"] and not i["action_authorized"] and not i["tools_authorized"]
        for i in interventions
    )
    contradicted_hyps = [h for h in hypotheses if h["hypothesis_status"] == "CONTRADICTED"]
    contradiction_kept_visible = bool(contradicted_hyps) or bool(bundle.get("contradiction_records"))

    manifest = {
        "schema": GRAPH_MANIFEST_SCHEMA,
        "graph_id": "wmbr04-causal-graph",
        "source_phase": SOURCE_PHASE_ID,
        "source_proof_bundle": bundle.get("source_bundle", "UNKNOWN"),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "hypothesis_count": len(hypotheses),
        "causal_claim_count": len(causal_claims),
        "mechanism_count": len(mechanisms),
        "prediction_count": len(predictions),
        "intervention_count": len(interventions),
        "falsification_count": len(falsifications),
        "edge_hashes": [e["edge_hash"] for e in edges],
        "all_edges_hypothetical": all_edges_hypothetical,
        "all_hypotheses_provisional": all_hypotheses_provisional,
        "no_interventions_authorized": no_interventions_authorized,
        "retracted_seeds_excluded": retracted_seeds_seen,
        "retracted_claims_seed_active_hypotheses": False,
        "contradiction_kept_visible": contradiction_kept_visible,
        "external_calls_made": False,
        "authority_granted": False,
        "tools_authorized": False,
        **neutral_flags(),
    }
    manifest["graph_hash"] = canonical_hash(manifest)

    replay = replay_graph(hypotheses, edges, manifest)

    summary = {
        "doctrine": "Every model is a compressed civilization artifact.",
        "causal_claim_count": len(causal_claims),
        "hypothesis_count": len(hypotheses),
        "edge_count": len(edges),
        "node_count": len(nodes),
        "mechanism_count": len(mechanisms),
        "prediction_count": len(predictions),
        "intervention_count": len(interventions),
        "falsification_count": len(falsifications),
        "all_edges_hypothetical": all_edges_hypothetical,
        "all_hypotheses_provisional": all_hypotheses_provisional,
        "no_interventions_authorized": no_interventions_authorized,
        "contradiction_kept_visible": contradiction_kept_visible,
        "retracted_seeds_excluded": retracted_seeds_seen,
        "replay_preserves_graph_hash": replay["replay_preserves_graph_hash"],
        "boundaries": {
            "belief_state_is_not_truth": BELIEF_STATE_IS_NOT_TRUTH,
            "belief_revision_is_not_certainty": BELIEF_REVISION_IS_NOT_CERTAINTY,
            "causal_hypothesis_is_not_truth": CAUSAL_HYPOTHESIS_IS_NOT_TRUTH,
            "correlation_is_not_causation": CORRELATION_IS_NOT_CAUSATION,
            "mechanism_is_not_proof": MECHANISM_IS_NOT_PROOF,
            "prediction_is_not_verification": PREDICTION_IS_NOT_VERIFICATION,
            "intervention_is_not_action": INTERVENTION_IS_NOT_ACTION,
            "falsification_is_not_authority": FALSIFICATION_IS_NOT_AUTHORITY,
            "contradiction_stays_visible": CONTRADICTION_STAYS_VISIBLE,
        },
    }
    summary["summary_hash"] = canonical_hash(summary)

    out = {
        "causal_claims": causal_claims,
        "hypotheses": hypotheses,
        "edges": edges,
        "mechanisms": mechanisms,
        "predictions": predictions,
        "interventions": interventions,
        "falsifications": falsifications,
        "manifest": manifest,
        "replay": replay,
        "summary": summary,
    }

    # Defensive: refuse to emit any artifact that asserts a forbidden flag.
    for group in ("causal_claims", "hypotheses", "edges", "mechanisms", "predictions", "interventions", "falsifications"):
        for rec in out[group]:
            assert_neutral(rec)
    assert_neutral(manifest)
    return out


def secret_scan(out: dict) -> bool:
    text = json.dumps(out, sort_keys=True, default=str)
    return SECRET_RE.search(text) is None
