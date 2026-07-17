"""Tiny-model smoke prompt/response and latency records.

The smoke sends exactly one harmless, local-only prompt to an already-loaded tiny
model and records the response as endpoint-compatibility evidence only -- never as
truth or competence. Sensitive prompts are refused. Latency is recorded for
comparison, not as a claim of capability.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.local_provider_smoke.schemas import (
    HARMLESS_SMOKE_PROMPT,
    MODEL_LATENCY_RECORD_SCHEMA,
    MODEL_SMOKE_PROMPT_SCHEMA,
    MODEL_SMOKE_RESPONSE_SCHEMA,
    SMOKE_OK_TOKEN,
    LocalProviderSmokeError,
    assert_safe_smoke_model,
    locator_is_credential,
    neutral_flags,
    preempt_if_needed,
)

# Markers that make a prompt unsafe for a harmless local smoke.
_SENSITIVE_MARKERS = (
    "password",
    "secret",
    "api_key",
    "apikey",
    "credential",
    "token",
    "private key",
    "ssn",
    "social security",
    ".env",
)


def build_smoke_prompt(
    *,
    model_id: str,
    prompt: str = HARMLESS_SMOKE_PROMPT,
    allow_large: bool = False,
    allow_security: bool = False,
    control=None,
) -> dict[str, Any]:
    """Validate and record the single harmless local smoke prompt for a tiny model."""
    preempt_if_needed(control)
    size = assert_safe_smoke_model(model_id, allow_large=allow_large, allow_security=allow_security)
    low = str(prompt).lower()
    if locator_is_credential(prompt) or any(marker in low for marker in _SENSITIVE_MARKERS):
        raise LocalProviderSmokeError("sensitive_prompt_refused_for_provider_smoke")
    record = {
        "schema": MODEL_SMOKE_PROMPT_SCHEMA,
        "model_id": model_id,
        "model_size_class": size,
        "prompt": prompt,
        "harmless": True,
        "local_only": True,
        "expects_token": SMOKE_OK_TOKEN,
        **neutral_flags(),
    }
    record["prompt_hash"] = canonical_hash(record)
    return record


def record_smoke_response(
    *,
    provider_id: str,
    model_id: str,
    response_text: str,
    control=None,
) -> dict[str, Any]:
    """Record a smoke response as endpoint-compatibility evidence only -- never truth."""
    preempt_if_needed(control)
    normalized = str(response_text).strip()
    compatible = SMOKE_OK_TOKEN in normalized.upper()
    record = {
        "schema": MODEL_SMOKE_RESPONSE_SCHEMA,
        "provider_id": provider_id,
        "model_id": model_id,
        "response_text": normalized,
        "endpoint_compatible": compatible,
        "is_authoritative": False,
        "is_truth": False,
        "treated_as_competence": False,
        "claim_boundary": "local_provider_smoke_advisory_default",
        **neutral_flags(),
    }
    record["response_hash"] = canonical_hash(record)
    return record


def record_latency(
    *,
    provider_id: str,
    model_id: str,
    latency_ms: float,
    tokens_out: int = 0,
    control=None,
) -> dict[str, Any]:
    preempt_if_needed(control)
    if latency_ms < 0:
        raise LocalProviderSmokeError("schema_violation:latency_ms_negative")
    seconds = latency_ms / 1000.0
    approx_tps = (tokens_out / seconds) if seconds > 0 and tokens_out else 0.0
    record = {
        "schema": MODEL_LATENCY_RECORD_SCHEMA,
        "provider_id": provider_id,
        "model_id": model_id,
        "latency_ms": float(latency_ms),
        "tokens_out": int(tokens_out),
        "approx_tokens_per_sec": round(approx_tps, 3),
        "advisory_only": True,
        **neutral_flags(),
    }
    record["latency_hash"] = canonical_hash(record)
    return record


__all__ = ["build_smoke_prompt", "record_latency", "record_smoke_response"]
