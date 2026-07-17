"""Provider output receipt tests."""
from __future__ import annotations

import pytest

from hg_runtime.live_provider.errors import LiveProviderNonCognitiveDenied, LiveProviderOutputError
from hg_runtime.live_provider.provider_identity import build_model_identity, build_provider_identity
from hg_runtime.live_provider.provider_receipts import (
    build_output_receipt,
    output_receipt_counts_as_cognition,
    verify_output_receipt_hash,
)
from hg_runtime.live_provider.schema import LiveProviderKind, LiveProviderVerdict, ProviderRuntimeMode


def test_output_receipt_hash_deterministic():
    provider = build_provider_identity(provider_kind=LiveProviderKind.HTTP_OPENAI_COMPATIBLE)
    model = build_model_identity(provider)
    r1 = build_output_receipt(
        request_ref="req-1",
        provider=provider,
        model=model,
        prompt_hash="ph",
        output_text='{"ok": true}',
        json_valid=True,
        latency_ms=10,
    )
    assert verify_output_receipt_hash(r1)


def test_empty_output_rejected():
    provider = build_provider_identity(provider_kind=LiveProviderKind.HTTP_OPENAI_COMPATIBLE)
    model = build_model_identity(provider)
    receipt = build_output_receipt(
        request_ref="req-2",
        provider=provider,
        model=model,
        prompt_hash="ph",
        output_text="",
        json_valid=False,
        latency_ms=1,
    )
    assert receipt.verdict == LiveProviderVerdict.YELLOW_PROVIDER_OUTPUT_EMPTY_DEFERRED
    assert not output_receipt_counts_as_cognition(receipt)


def test_fallback_rejected_as_cognition():
    provider = build_provider_identity(provider_kind=LiveProviderKind.HTTP_OPENAI_COMPATIBLE)
    model = build_model_identity(provider)
    with pytest.raises(LiveProviderNonCognitiveDenied):
        build_output_receipt(
            request_ref="req-3",
            provider=provider,
            model=model,
            prompt_hash="ph",
            output_text="fallback text",
            json_valid=True,
            latency_ms=1,
            source_label="fallback",
        )


def test_fixture_rejected_as_cognition():
    provider = build_provider_identity(provider_kind=LiveProviderKind.HTTP_OPENAI_COMPATIBLE)
    model = build_model_identity(provider)
    with pytest.raises(LiveProviderNonCognitiveDenied):
        build_output_receipt(
            request_ref="req-4",
            provider=provider,
            model=model,
            prompt_hash="ph",
            output_text="fixture",
            json_valid=True,
            latency_ms=1,
            source_label="fixture",
        )


def test_missing_provider_id_rejected():
    from hg_runtime.live_provider.schema import ProviderIdentity, LiveProviderKind, ProviderRuntimeMode

    bad = ProviderIdentity(
        provider_id="",
        provider_kind=LiveProviderKind.DRY_UNAVAILABLE,
        provider_name="x",
        transport="none",
        runtime_mode=ProviderRuntimeMode.DRY_AUTONOMY,
    )
    model = build_model_identity(build_provider_identity())
    with pytest.raises(LiveProviderOutputError):
        build_output_receipt(
            request_ref="req-5",
            provider=bad,
            model=model,
            prompt_hash="ph",
            output_text="{}",
            json_valid=True,
            latency_ms=1,
        )
