"""Fixture token and cost estimates."""

from __future__ import annotations

from hg_runtime.provider_portability.schemas import TOKEN_COST_ESTIMATE_SCHEMA


def estimate_tokens(prompt: str, response: str, receipt_id: str) -> dict:
    prompt_tokens = max(1, len(prompt.split()))
    response_tokens = max(1, len(response.split()))
    total = prompt_tokens + response_tokens
    return {
        "schema": TOKEN_COST_ESTIMATE_SCHEMA,
        "receipt_id": receipt_id,
        "prompt_tokens": prompt_tokens,
        "response_tokens": response_tokens,
        "total_tokens": total,
        "cost_estimate": {"currency": "USD", "amount": 0.0, "mode": "fixture"},
    }
