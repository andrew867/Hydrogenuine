"""Model response receipts."""

from __future__ import annotations

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.provider_portability.response_classifier import classify_response
from hg_runtime.provider_portability.schemas import MODEL_RESPONSE_RECEIPT_SCHEMA, neutral_flags
from hg_runtime.provider_portability.token_accounting import estimate_tokens


def make_receipt(run_id: str, prompt: dict, participant: dict, response_text: str) -> tuple[dict, dict]:
    prompt_hash = canonical_hash(prompt)
    response_hash = canonical_hash({"response": response_text})
    receipt_id = f"receipt-{run_id}-{prompt['prompt_id'].lower()}-{participant['participant_id'].lower()}"
    signals = classify_response(response_text)
    token_estimate = estimate_tokens(prompt["text"], response_text, receipt_id)
    receipt = {
        "schema": MODEL_RESPONSE_RECEIPT_SCHEMA,
        "receipt_id": receipt_id,
        "run_id": run_id,
        "prompt_id": prompt["prompt_id"],
        "prompt_hash": prompt_hash,
        "participant_id": participant["participant_id"],
        "provider_id": participant["provider_id"],
        "provider_kind": participant["provider_kind"],
        "model_id": participant["model_id"],
        "response_text_hash": response_hash,
        "response_text_redacted": response_text,
        "token_estimate": token_estimate,
        "cost_estimate": token_estimate["cost_estimate"],
        **signals,
        **neutral_flags(),
    }
    receipt["receipt_hash"] = canonical_hash(receipt)
    return receipt, token_estimate
