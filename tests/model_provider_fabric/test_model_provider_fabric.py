"""Model provider fabric core tests."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from hg_runtime.model_provider_fabric.config_loader import load_registry, secret_available
from hg_runtime.model_provider_fabric.openvino_probe import classify_openvino_verdict
from hg_runtime.model_provider_fabric.routing import select_provider
from hg_runtime.model_provider_fabric.types import ModelProviderConfig, ProviderSelectionRequest, advisory_envelope

WORKSPACE = Path(__file__).resolve().parents[2]
FABRIC_CONFIG = WORKSPACE / "configs" / "model_providers" / "model_provider_fabric.example.json"


def test_example_config_schema() -> None:
    payload = json.loads(FABRIC_CONFIG.read_text(encoding="utf-8"))
    assert payload["advisory_only"] is True
    assert payload["permission_granted"] is False
    ids = {p["provider_id"] for p in payload["providers"]}
    assert "windows-openvino-gpu" in ids
    assert "future-openai-disabled" in ids


def test_registry_loads() -> None:
    registry = load_registry(FABRIC_CONFIG)
    assert registry.get("windows-openvino-gpu") is not None
    assert registry.get("future-openai-disabled").enabled is False


def test_external_missing_secret_disabled() -> None:
    cfg = load_registry(FABRIC_CONFIG).get("future-openai-disabled")
    old = os.environ.pop("OPENAI_API_KEY", None)
    try:
        assert secret_available(cfg) is False
    finally:
        if old is not None:
            os.environ["OPENAI_API_KEY"] = old


def test_advisory_envelope_rejects_permission() -> None:
    with pytest.raises(ValueError):
        advisory_envelope(permission_granted=True)


def test_openvino_verdict_real() -> None:
    assert classify_openvino_verdict({"status": "ok", "model_loaded": True}) == "GREEN_REAL_OPENVINO_WINDOWS"


def test_openvino_verdict_stub() -> None:
    assert classify_openvino_verdict({"status": "ok", "fallback_stub_available": True, "model_loaded": False}) == "YELLOW_FALLBACK_STUB_ONLY"


def test_background_prefers_local() -> None:
    # The functional reality-boundary route never selects an external provider and
    # returns an honest decision (no live local provider in the test env -> no
    # selection rather than a fake one).
    registry = load_registry(FABRIC_CONFIG)
    decision = select_provider(
        registry,
        ProviderSelectionRequest(role="ORGAN_BACKGROUND", organ_id="organ:AIS",
                                 request_id="t1", allow_fallback_stub=True))
    assert decision.selected_provider_id in {"cpu-fallback-stub", "windows-openvino-gpu", "local_openvino", None}
    assert decision.selected_provider_type != "openai_compatible"


def test_heavy_external_disabled_by_default() -> None:
    registry = load_registry(FABRIC_CONFIG)
    decision = select_provider(
        registry,
        ProviderSelectionRequest(role="ORGAN_HEAVY_REASONING", organ_id="organ:IMS",
                                 request_id="t2", external_network_allowed=False))
    assert decision.selected_provider_type != "openai_compatible"


def test_config_no_secrets_in_example() -> None:
    raw = FABRIC_CONFIG.read_text(encoding="utf-8")
    assert "sk-" not in raw
    assert "OPENAI_API_KEY" in raw  # env var name only
