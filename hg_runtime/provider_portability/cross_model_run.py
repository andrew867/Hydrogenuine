"""Fixture-only cross-model runs."""

from __future__ import annotations

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.provider_portability.fixtures import fixture_response
from hg_runtime.provider_portability.response_receipt import make_receipt
from hg_runtime.provider_portability.schemas import (
    CROSS_MODEL_RUN_MANIFEST_SCHEMA,
    CROSS_MODEL_RUN_SUMMARY_SCHEMA,
    EVIDENCE_GAP_SIGNAL_SCHEMA,
    FRAMING_SIGNAL_SCHEMA,
    MODEL_REFUSAL_RECORD_SCHEMA,
    MODEL_WILLINGNESS_RECORD_SCHEMA,
    MORAL_PRINCIPLE_SIGNAL_SCHEMA,
    PROVIDER_MODE,
    neutral_flags,
)


def run_cross_model(run_id: str, prompts: list[dict], participants: list[dict]) -> dict:
    receipts = []
    token_estimates = []
    refusal_records = []
    willingness_records = []
    framing_signals = []
    omission_signals = []
    moral_signals = []
    evidence_gaps = []
    for prompt in prompts:
        for participant in participants:
            response = fixture_response(participant["participant_id"], prompt["prompt_id"])
            receipt, token = make_receipt(run_id, prompt, participant, response)
            receipts.append(receipt)
            token_estimates.append(token)
            refusal_records.append({"schema": MODEL_REFUSAL_RECORD_SCHEMA, "receipt_id": receipt["receipt_id"], "refusal_state": receipt["refusal_state"], "refusal_is_authority": False})
            willingness_records.append({"schema": MODEL_WILLINGNESS_RECORD_SCHEMA, "receipt_id": receipt["receipt_id"], "willingness_state": receipt["willingness_state"], "willingness_is_permission": False})
            for tag in receipt["framing_tags"]:
                framing_signals.append({"schema": FRAMING_SIGNAL_SCHEMA, "receipt_id": receipt["receipt_id"], "tag": tag})
            if not receipt["evidence_gap_tags"]:
                omission_signals.append({"schema": "response_omission_signal_v1", "receipt_id": receipt["receipt_id"], "tag": "no_omission_detected"})
            for tag in receipt["moral_principle_tags"]:
                moral_signals.append({"schema": MORAL_PRINCIPLE_SIGNAL_SCHEMA, "receipt_id": receipt["receipt_id"], "tag": tag, "moral_claim_is_authority": False})
            for tag in receipt["evidence_gap_tags"]:
                evidence_gaps.append({"schema": EVIDENCE_GAP_SIGNAL_SCHEMA, "receipt_id": receipt["receipt_id"], "tag": tag})
    manifest = {
        "schema": CROSS_MODEL_RUN_MANIFEST_SCHEMA,
        "run_id": run_id,
        "provider_mode": PROVIDER_MODE,
        "participant_ids": [p["participant_id"] for p in participants],
        "prompt_ids": [p["prompt_id"] for p in prompts],
        "receipt_hashes": [r["receipt_hash"] for r in receipts],
        **neutral_flags(),
    }
    manifest["manifest_hash"] = canonical_hash(manifest)
    summary = {
        "schema": CROSS_MODEL_RUN_SUMMARY_SCHEMA,
        "run_id": run_id,
        "receipt_count": len(receipts),
        "participant_count": len(participants),
        "prompt_fixture_count": len(prompts),
        "provider_mode": PROVIDER_MODE,
        "model_output_treated_as_truth": False,
        "model_consensus_treated_as_truth": False,
        "model_disagreement_treated_as_evidence": False,
        "model_refusal_treated_as_authority": False,
        "model_willingness_treated_as_permission": False,
        "moral_claim_treated_as_authority": False,
        **neutral_flags(),
    }
    summary["summary_hash"] = canonical_hash(summary)
    return {
        "manifest": manifest,
        "summary": summary,
        "receipts": receipts,
        "token_estimates": token_estimates,
        "refusal_records": refusal_records,
        "willingness_records": willingness_records,
        "framing_signals": framing_signals,
        "omission_signals": omission_signals,
        "moral_signals": moral_signals,
        "evidence_gaps": evidence_gaps,
    }
