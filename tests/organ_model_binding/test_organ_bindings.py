"""Organ model binding tests."""

from __future__ import annotations

from hg_runtime.model_provider_fabric.organ_binding import binding_for_organ, all_bindings
from hg_runtime.model_provider_fabric.config_loader import load_registry
from hg_runtime.model_provider_fabric.routing import select_provider
from hg_runtime.model_provider_fabric.types import ProviderSelectionRequest
from pathlib import Path

FABRIC_CONFIG = Path(__file__).resolve().parents[2] / "configs" / "model_providers" / "model_provider_fabric.example.json"


def test_agent0_wake_binding() -> None:
    b = binding_for_organ("organ:Agent0")
    assert b is not None
    assert b.primary_role == "AGENT0_WAKE"


def test_ais_background_binding() -> None:
    b = binding_for_organ("organ:AIS")
    assert b is not None
    assert b.primary_role == "ORGAN_BACKGROUND"


def test_all_bindings_advisory() -> None:
    for binding in all_bindings():
        payload = binding.to_payload()
        assert payload["permission_granted"] is False
        assert payload["authority_created"] is False


def test_organ_routing_emits_decision() -> None:
    registry = load_registry(FABRIC_CONFIG)
    binding = binding_for_organ("organ:HRT")
    assert binding is not None
    decision = select_provider(
        registry,
        ProviderSelectionRequest(
            role=binding.primary_role,
            organ_id=binding.organ_id,
            request_id="organ:test",
            allow_fallback_stub=True,
        ),
    )
    assert decision.role == "ORGAN_BACKGROUND"
