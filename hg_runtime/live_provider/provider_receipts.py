"""Provider output receipts — mandatory for real cognition."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.live_provider.errors import LiveProviderNonCognitiveDenied, LiveProviderOutputError
from hg_runtime.live_provider.schema import (
    LiveProviderVerdict,
    ModelIdentity,
    ProviderIdentity,
    ProviderOutputReceipt,
    load_live_provider_policy,
    new_id,
    now_iso,
)

WORKSPACE = Path(__file__).resolve().parents[2]
OUTPUT_DIR = Path(".hg-local/agent_zero/live_provider/output")


def _output_store_path() -> Path:
    root = WORKSPACE / OUTPUT_DIR
    root.mkdir(parents=True, exist_ok=True)
    return root


def hash_text(text: str) -> str:
    return compute_record_hash({"text": text})


def build_output_receipt(
    *,
    request_ref: str,
    provider: ProviderIdentity,
    model: ModelIdentity,
    prompt_hash: str,
    output_text: str,
    json_valid: bool,
    latency_ms: int,
    schema_valid: bool | None = None,
    token_counts: dict[str, int] | None = None,
    finish_reason: str | None = None,
    raw_response_ref: str | None = None,
    source_label: str | None = None,
) -> ProviderOutputReceipt:
    """Build provider output receipt with identity and hashes."""
    policy = load_live_provider_policy()
    if not provider.provider_id:
        raise LiveProviderOutputError("RED_PROVIDER_IDENTITY_MISSING")
    if not model.model_id:
        raise LiveProviderOutputError("RED_MODEL_IDENTITY_MISSING")

    if source_label in ("fallback", "fixture", "mock"):
        raise LiveProviderNonCognitiveDenied(f"RED_{source_label.upper()}_TEXT_TREATED_AS_COGNITION")

    if not output_text or not str(output_text).strip():
        return ProviderOutputReceipt(
            provider_output_receipt_id=new_id("output-rcpt"),
            request_ref=request_ref,
            provider_ref=provider.provider_id,
            model_ref=model.model_id,
            prompt_hash=prompt_hash,
            response_hash=compute_record_hash({"empty": True}),
            output_text_hash=hash_text(""),
            json_valid=False,
            latency_ms=latency_ms,
            verdict=LiveProviderVerdict.YELLOW_PROVIDER_OUTPUT_EMPTY_DEFERRED,
        ).with_hash()

    if policy.get("empty_output_allowed_as_success") is False and not output_text.strip():
        return ProviderOutputReceipt(
            provider_output_receipt_id=new_id("output-rcpt"),
            request_ref=request_ref,
            provider_ref=provider.provider_id,
            model_ref=model.model_id,
            prompt_hash=prompt_hash,
            response_hash=compute_record_hash({"empty": True}),
            output_text_hash=hash_text(output_text),
            json_valid=False,
            latency_ms=latency_ms,
            verdict=LiveProviderVerdict.YELLOW_PROVIDER_OUTPUT_EMPTY_DEFERRED,
        ).with_hash()

    verdict = LiveProviderVerdict.GREEN_LIVE_PROVIDER_OUTPUT_VALID
    if not json_valid and policy.get("invalid_json_allowed_as_success") is False:
        verdict = LiveProviderVerdict.YELLOW_PROVIDER_JSON_INVALID_DEFERRED

    receipt = ProviderOutputReceipt(
        provider_output_receipt_id=new_id("output-rcpt"),
        request_ref=request_ref,
        provider_ref=provider.provider_id,
        model_ref=model.model_id,
        prompt_hash=prompt_hash,
        response_hash=compute_record_hash({"output": output_text}),
        raw_response_ref=raw_response_ref,
        output_text_hash=hash_text(output_text),
        json_valid=json_valid,
        schema_valid=schema_valid,
        latency_ms=latency_ms,
        token_counts=token_counts,
        finish_reason=finish_reason,
        created_at=now_iso(),
        verdict=verdict,
    ).with_hash()
    return receipt


def store_output_receipt(receipt: ProviderOutputReceipt, *, output_text: str | None = None) -> Path:
    root = _output_store_path()
    path = root / f"{receipt.provider_output_receipt_id}.json"
    path.write_text(json.dumps(receipt.to_payload(), indent=2), encoding="utf-8")
    if output_text is not None:
        raw_path = root / f"{receipt.provider_output_receipt_id}.raw.txt"
        raw_path.write_text(output_text, encoding="utf-8")
    return path


def load_output_receipt(receipt_id: str) -> ProviderOutputReceipt | None:
    path = _output_store_path() / f"{receipt_id}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return ProviderOutputReceipt(
        provider_output_receipt_id=data["provider_output_receipt_id"],
        request_ref=data["request_ref"],
        provider_ref=data["provider_ref"],
        model_ref=data["model_ref"],
        prompt_hash=data["prompt_hash"],
        response_hash=data["response_hash"],
        raw_response_ref=data.get("raw_response_ref"),
        output_text_hash=data["output_text_hash"],
        json_valid=data["json_valid"],
        schema_valid=data.get("schema_valid"),
        latency_ms=data["latency_ms"],
        token_counts=data.get("token_counts"),
        finish_reason=data.get("finish_reason"),
        created_at=data["created_at"],
        verdict=LiveProviderVerdict(data["verdict"]),
        hash=data.get("hash"),
    )


def verify_output_receipt_hash(receipt: ProviderOutputReceipt) -> bool:
    body = {k: v for k, v in receipt.to_payload().items() if k != "hash"}
    expected = compute_record_hash(body)
    return receipt.hash == expected


def output_receipt_counts_as_cognition(receipt: ProviderOutputReceipt) -> bool:
    policy = load_live_provider_policy()
    if receipt.verdict != LiveProviderVerdict.GREEN_LIVE_PROVIDER_OUTPUT_VALID:
        return False
    if not receipt.json_valid and policy.get("invalid_json_allowed_as_success") is False:
        return False
    if not receipt.provider_ref or not receipt.model_ref:
        return False
    return verify_output_receipt_hash(receipt)
