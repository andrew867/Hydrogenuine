"""P32-1 model registry and resource preflight tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_GATE_PATH = Path(__file__).resolve().parents[2] / "scripts/evals/autonomous_agent_p32_1_model_registry_preflight_gate.py"
_spec = importlib.util.spec_from_file_location("p32_1_gate", _GATE_PATH)
p32_1_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p32_1_gate)

from hg_runtime.model_routing.schemas import MODEL_ROLES, ModelRoutingBoundaryError
from hg_runtime.model_routing.model_registry import (
    builtin_registry,
    create_registry_entry,
    preflight_check,
)
from hg_runtime.model_routing.gate import validate_p32_1_gate


# --- Gate run ----------------------------------------------------------------

class TestP32_1GateRun:
    def test_gate_green(self):
        code, summary = p32_1_gate.run_gate()
        assert code == 0
        assert summary["verdict"] == "GREEN_P32_1_MODEL_REGISTRY_PREFLIGHT"
        assert summary["ok"] is True

    def test_p32_0_dependency(self):
        _, summary = p32_1_gate.run_gate()
        assert summary["p32_0_green"] is True

    def test_registry_populated(self):
        _, summary = p32_1_gate.run_gate()
        assert summary["registry_populated"] is True
        assert summary["all_roles_covered"] is True

    def test_no_providers(self):
        _, summary = p32_1_gate.run_gate()
        assert summary["no_providers_enabled"] is True


# --- Registry ----------------------------------------------------------------

class TestModelRegistry:
    def test_builtin_covers_all_roles(self):
        registry = builtin_registry()
        roles = {e["role"] for e in registry}
        assert roles == MODEL_ROLES

    def test_all_disabled(self):
        for e in builtin_registry():
            assert e["provider_state"] == "disabled"
            assert e["tier"] == "local_fixture"

    def test_entry_flags(self):
        for e in builtin_registry():
            assert e["model_output_is_not_truth"] is True
            assert e["model_selection_is_not_authority"] is True
            assert "entry_hash" in e

    def test_invalid_role(self):
        with pytest.raises(ModelRoutingBoundaryError):
            create_registry_entry(model_id="x", role="agi_god")

    def test_invalid_tier(self):
        with pytest.raises(ModelRoutingBoundaryError):
            create_registry_entry(model_id="x", role="planner", tier="cloud_mega")


# --- Preflight ---------------------------------------------------------------

class TestPreflight:
    def test_full_coverage(self):
        pf = preflight_check(builtin_registry())
        assert pf["all_roles_covered"] is True
        assert pf["providers_enabled"] is False
        assert pf["preflight_ok"] is True

    def test_partial_coverage(self):
        entry = create_registry_entry(model_id="m1", role="planner")
        pf = preflight_check([entry])
        assert pf["all_roles_covered"] is False
        assert len(pf["missing_roles"]) > 0

    def test_preflight_not_authority(self):
        pf = preflight_check(builtin_registry())
        assert pf["preflight_is_not_authority"] is True


# --- Gate validator -----------------------------------------------------------

class TestGateValidator:
    def _summary(self, **overrides):
        data = {
            "p32_0_green": True,
            "registry_populated": True,
            "preflight_ok": True,
            "all_roles_covered": True,
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
        result = validate_p32_1_gate(self._summary())
        assert result["ok"] is True

    def test_missing_p32_0_fails(self):
        result = validate_p32_1_gate(self._summary(p32_0_green=False))
        assert result["ok"] is False

    def test_preflight_fail(self):
        result = validate_p32_1_gate(self._summary(preflight_ok=False))
        assert result["ok"] is False
