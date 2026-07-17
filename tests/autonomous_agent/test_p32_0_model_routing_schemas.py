"""P32-0 model routing schemas tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_GATE_PATH = Path(__file__).resolve().parents[2] / "scripts/evals/autonomous_agent_p32_0_model_routing_schema_gate.py"
_spec = importlib.util.spec_from_file_location("p32_0_gate", _GATE_PATH)
p32_0_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p32_0_gate)

from hg_runtime.model_routing.schemas import (
    MODEL_ROLES,
    ROUTING_MODES,
    PROVIDER_STATES,
    ROUTE_RESULT_STATES,
    MODEL_TIERS,
    P32_INVARIANTS,
    ModelRoutingBoundaryError,
)
from hg_runtime.model_routing.routing_policy import create_routing_policy
from hg_runtime.model_routing.gate import validate_p32_0_gate


# --- Gate run ----------------------------------------------------------------

class TestP32_0GateRun:
    def test_gate_green(self):
        code, summary = p32_0_gate.run_gate()
        assert code == 0
        assert summary["verdict"] == "GREEN_P32_0_MODEL_ROUTING_SCHEMAS"
        assert summary["ok"] is True
        assert summary["failures"] == []

    def test_p31_dependency(self):
        _, summary = p32_0_gate.run_gate()
        assert summary["p31_consolidation_green"] is True

    def test_phase19_yellow(self):
        _, summary = p32_0_gate.run_gate()
        assert summary["phase19_yellow_preserved"] is True

    def test_no_providers(self):
        _, summary = p32_0_gate.run_gate()
        assert summary["no_providers_enabled"] is True


# --- Schema constants --------------------------------------------------------

class TestSchemaConstants:
    def test_model_roles(self):
        assert len(MODEL_ROLES) >= 5
        assert "planner" in MODEL_ROLES
        assert "coder" in MODEL_ROLES

    def test_routing_modes(self):
        assert "fixture_only" in ROUTING_MODES
        assert "policy_only" in ROUTING_MODES

    def test_provider_states(self):
        assert "disabled" in PROVIDER_STATES

    def test_route_result_states(self):
        assert "ROUTED" in ROUTE_RESULT_STATES
        assert "REFUSED" in ROUTE_RESULT_STATES

    def test_model_tiers(self):
        assert "local_fixture" in MODEL_TIERS
        assert "remote_disabled" in MODEL_TIERS

    def test_invariants(self):
        assert len(P32_INVARIANTS) >= 10
        assert "model_selection_is_not_authority" in P32_INVARIANTS


# --- Routing policy ----------------------------------------------------------

class TestRoutingPolicy:
    def test_create_default(self):
        p = create_routing_policy()
        assert p["schema"] == "routing_policy_v1"
        assert p["routing_mode"] == "fixture_only"
        assert p["provider_state"] == "disabled"
        assert "policy_hash" in p

    def test_advisory_flags(self):
        p = create_routing_policy()
        assert p["model_selection_is_not_authority"] is True
        assert p["routing_recommendation_is_advisory"] is True

    def test_invalid_mode(self):
        with pytest.raises(ModelRoutingBoundaryError):
            create_routing_policy(routing_mode="live_cloud")

    def test_invalid_provider(self):
        with pytest.raises(ModelRoutingBoundaryError):
            create_routing_policy(provider_state="enabled")

    def test_invalid_role(self):
        with pytest.raises(ModelRoutingBoundaryError):
            create_routing_policy(allowed_roles=frozenset({"agi_overlord"}))


# --- Gate validator -----------------------------------------------------------

class TestGateValidator:
    def _summary(self, **overrides):
        data = {
            "p31_consolidation_green": True,
            "schemas_defined": True,
            "policy_created": True,
            "model_selection_is_not_authority": True,
            "routing_recommendation_is_advisory": True,
            "no_providers_enabled": True,
            "no_route_reads_hg_local": True,
            "phase19_yellow_preserved": True,
            "phase24_infrastructure_only_preserved": True,
            "secret_redaction_passed": True,
            "proof_bundle_valid": True,
            "report_present": True,
        }
        data.update(overrides)
        return data

    def test_valid_passes(self):
        result = validate_p32_0_gate(self._summary())
        assert result["ok"] is True

    def test_missing_p31_fails(self):
        result = validate_p32_0_gate(self._summary(p31_consolidation_green=False))
        assert result["ok"] is False

    def test_providers_enabled_fails(self):
        result = validate_p32_0_gate(self._summary(no_providers_enabled=False))
        assert result["ok"] is False
