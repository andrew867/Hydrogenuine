"""Provider empty output tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_core.infer_live.config import infer_dry_run_mode  # noqa: E402
from hg_runtime.live_inference_runtime.hardware import detect_hardware_profile  # noqa: E402
from hg_runtime.live_inference_runtime.adapter import run_dry_run_inference  # noqa: E402
from hg_runtime.live_inference_runtime.types import InferenceRuntimeRequest  # noqa: E402
from hg_runtime.model_provider_fabric.provider_receipts import (  # noqa: E402
    ProviderOutputVerdict,
    ProviderRealityVerdict,
)
from hg_runtime.model_provider_fabric.provider_reality import evaluate_provider_output  # noqa: E402
from hg_runtime.model_provider_fabric.provider_receipts import (  # noqa: E402
    ProviderKind,
    ProviderMode,
    ProviderStatus,
    build_provider_receipt,
)


def test_empty_output_red():
    receipt = build_provider_receipt(
        provider_id="test",
        provider_kind=ProviderKind.STUB,
        provider_mode=ProviderMode.LIVE,
        role="AGENT_TURN_DECISION",
        request_hash="req",
        config_hash="cfg",
        runtime_mode="local_dev",
        cognitive_soak_active=False,
        dry_run=False,
        fixture_mode=False,
        status=ProviderStatus.AVAILABLE,
        verdict=ProviderRealityVerdict.RED_PROVIDER_EMPTY_OUTPUT,
    )
    verdict = evaluate_provider_output(role="AGENT_TURN_DECISION", output_text="", receipt=receipt)
    assert verdict == ProviderOutputVerdict.RED_OUTPUT_NOT_COGNITION


def test_output_without_receipt_rejected():
    verdict = evaluate_provider_output(role="AGENT_TURN_DECISION", output_text="some output", receipt=None)
    assert verdict == ProviderOutputVerdict.RED_OUTPUT_WITHOUT_RECEIPT


def test_dry_run_inference_cannot_produce_green_cognition(monkeypatch):
    monkeypatch.setenv("HG_INFER_DRY_RUN", "1")
    assert infer_dry_run_mode() is True
    req = InferenceRuntimeRequest(
        request_id="dry-run-test-1",
        organ_ref="AGENT_DRAFT_WRITE",
        model_profile_id="default",
        operator_ref=None,
        freshness_ref=None,
        approval_expires_at=None,
        dry_run=True,
    )
    hw = detect_hardware_profile(fixture={"profile_id": "t", "igpu_available": True, "ram_gb": 32, "meets_minimum_profile": True})
    result = run_dry_run_inference(req, hw)
    assert result.get("counts_as_cognition") is False
    assert result.get("dry_run") is True
    assert result["provider_receipt"]["verdict"] == ProviderRealityVerdict.YELLOW_PROVIDER_DRY_RUN_LABELLED.value
