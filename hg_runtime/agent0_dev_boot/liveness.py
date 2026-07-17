"""Agent #0 liveness response wrapper — safe dev statement, raw hash retained."""

from __future__ import annotations

import hashlib
from typing import Any

from hg_runtime.agent0_dev_boot.types import advisory_payload

WRAPPER_TEXT = "omg yes I am awake in dev mode, thanks for asking"


def _hash_text(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


def wrap_liveness_response(
    *,
    raw_model_response: str,
    provider_id: str,
    model_id: str,
    fallback_stub: bool,
    resolved_device: str | None = None,
) -> dict[str, Any]:
    wrapper = WRAPPER_TEXT
    return advisory_payload(
        schema="agent0-liveness-response",
        wrapper_response=wrapper,
        wrapper_response_hash=_hash_text(wrapper),
        raw_model_response_hash=_hash_text(raw_model_response),
        raw_model_response_ref="hash-only",
        provider_id=provider_id,
        model_id=model_id,
        source_provider=provider_id,
        fallback_stub=fallback_stub,
        resolved_device=resolved_device,
        consciousness_claim=False,
        authority_claim=False,
    )


__all__ = ["WRAPPER_TEXT", "wrap_liveness_response"]
