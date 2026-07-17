"""Provider fallback denial tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.model_provider_fabric.provider_receipts import (  # noqa: E402
    ProviderRealityVerdict,
    receipt_counts_as_cognition,
)
from hg_runtime.model_provider_fabric.provider_reality import probe_provider_reality  # noqa: E402
from hg_runtime.model_provider_fabric.routing import route_to_verdict  # noqa: E402
from hg_runtime.runtime_mode import RuntimeMode  # noqa: E402
from hg_runtime.tool_capability_fabric.tools import model_inference_tool_stub  # noqa: E402


@pytest.fixture(autouse=True)
def _safe_env(monkeypatch):
    monkeypatch.setenv("HG_RUNTIME_MODE", "local_dev")
    monkeypatch.setenv("HG_INFER_DRY_RUN", "0")
    monkeypatch.setenv("HG_PROVIDER_LOCAL_OPENVINO_CONFIGURED", "false")
    monkeypatch.delenv("HG_ALLOW_FIXTURE_MODE", raising=False)


def test_fallback_stub_denied_for_agent_turn_decision():
    verdict, _, mode = route_to_verdict("AGENT_TURN_DECISION", runtime_mode=RuntimeMode.LOCAL_DEV)
    if verdict == ProviderRealityVerdict.RED_PROVIDER_FALLBACK_AS_COGNITION:
        assert mode.value == "fallback_stub"
    else:
        assert verdict in (
            ProviderRealityVerdict.YELLOW_PROVIDER_UNAVAILABLE,
            ProviderRealityVerdict.RED_PROVIDER_FALLBACK_AS_COGNITION,
        )


def test_fixture_denied_for_cognitive_role_outside_fixture_mode(monkeypatch):
    monkeypatch.setenv("HG_RUNTIME_MODE", "fixture")
    monkeypatch.setenv("HG_ALLOW_FIXTURE_MODE", "true")
    verdict, _, _ = route_to_verdict("AGENT_TURN_DECISION")
    assert verdict == ProviderRealityVerdict.RED_PROVIDER_FIXTURE_AS_COGNITION


def test_cognitive_soak_active_blocks_fallback(monkeypatch):
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "1")
    receipt = probe_provider_reality("AGENT_TURN_DECISION")
    assert receipt.cognitive_soak_active is True
    assert receipt.verdict != ProviderRealityVerdict.GREEN_PROVIDER_LIVE_AVAILABLE


def test_tool_model_stub_cannot_produce_green_cognition():
    result = model_inference_tool_stub(prompt="test", role="AGENT_TURN_DECISION")
    assert result["counts_as_cognition"] is False
    assert result["result"]["provider_receipt"]["verdict"] == ProviderRealityVerdict.RED_PROVIDER_FALLBACK_AS_COGNITION.value
    receipt_verdict = result["result"]["provider_receipt"]["verdict"]
    assert receipt_verdict != ProviderRealityVerdict.GREEN_PROVIDER_LIVE_AVAILABLE.value
