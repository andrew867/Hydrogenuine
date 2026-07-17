"""Provider receipt tests."""

from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.model_provider_fabric.provider_receipts import (  # noqa: E402
    ProviderKind,
    ProviderMode,
    ProviderRealityVerdict,
    ProviderStatus,
    build_provider_receipt,
    receipt_counts_as_cognition,
    validate_provider_receipt,
)


def test_provider_receipt_has_identity_mode_verdict_hash():
    receipt = build_provider_receipt(
        provider_id="test-provider",
        provider_kind=ProviderKind.LOCAL_OPENVINO,
        provider_mode=ProviderMode.LIVE,
        role="AGENT_TURN_DECISION",
        request_hash="req-hash-abc",
        config_hash="cfg-hash-xyz",
        runtime_mode="local_dev",
        cognitive_soak_active=False,
        dry_run=False,
        fixture_mode=False,
        status=ProviderStatus.AVAILABLE,
        verdict=ProviderRealityVerdict.GREEN_PROVIDER_LIVE_AVAILABLE,
    )
    assert receipt.provider_id == "test-provider"
    assert receipt.provider_mode == ProviderMode.LIVE
    assert receipt.verdict == ProviderRealityVerdict.GREEN_PROVIDER_LIVE_AVAILABLE
    assert receipt.request_hash == "req-hash-abc"
    assert validate_provider_receipt(receipt) == ProviderRealityVerdict.GREEN_PROVIDER_LIVE_AVAILABLE


def test_provider_receipt_required_for_cognitive_output():
    assert validate_provider_receipt(None) == ProviderRealityVerdict.RED_PROVIDER_RECEIPT_MISSING


def test_no_hidden_chain_of_thought_field_stored():
    receipt = build_provider_receipt(
        provider_id="test-provider",
        provider_kind=ProviderKind.LOCAL_OPENVINO,
        provider_mode=ProviderMode.LIVE,
        role="AGENT_TURN_DECISION",
        request_hash="req",
        config_hash="cfg",
        runtime_mode="local_dev",
        cognitive_soak_active=False,
        dry_run=False,
        fixture_mode=False,
        status=ProviderStatus.AVAILABLE,
        verdict=ProviderRealityVerdict.GREEN_PROVIDER_LIVE_AVAILABLE,
    )
    payload = receipt.to_payload()
    assert "chain_of_thought" not in payload
    assert "hidden_reasoning" not in payload


def test_live_receipt_counts_as_cognition():
    receipt = build_provider_receipt(
        provider_id="live",
        provider_kind=ProviderKind.LOCAL_OPENVINO,
        provider_mode=ProviderMode.LIVE,
        role="AGENT_TURN_DECISION",
        request_hash="req",
        config_hash="cfg",
        runtime_mode="local_dev",
        cognitive_soak_active=False,
        dry_run=False,
        fixture_mode=False,
        status=ProviderStatus.AVAILABLE,
        verdict=ProviderRealityVerdict.GREEN_PROVIDER_LIVE_AVAILABLE,
    )
    assert receipt_counts_as_cognition(receipt) is True
