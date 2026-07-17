"""P32-2 route decision and refusal policy tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_GATE_PATH = Path(__file__).resolve().parents[2] / "scripts/evals/autonomous_agent_p32_2_route_decision_refusal_gate.py"
_spec = importlib.util.spec_from_file_location("p32_2_gate", _GATE_PATH)
p32_2_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p32_2_gate)

from hg_runtime.model_routing.schemas import MODEL_ROLES, ModelRoutingBoundaryError
from hg_runtime.model_routing.model_registry import builtin_registry
from hg_runtime.model_routing.route_decision import (
    create_route_request,
    route_to_model,
    refuse_authority_claim,
)
from hg_runtime.model_routing.gate import validate_p32_2_gate


# --- Gate run ----------------------------------------------------------------

class TestP32_2GateRun:
    def test_gate_green(self):
        code, summary = p32_2_gate.run_gate()
        assert code == 0
        assert summary["verdict"] == "GREEN_P32_2_ROUTE_DECISION_REFUSAL"
        assert summary["ok"] is True

    def test_p32_1_dependency(self):
        _, summary = p32_2_gate.run_gate()
        assert summary["p32_1_green"] is True

    def test_routes_tested(self):
        _, summary = p32_2_gate.run_gate()
        assert summary["routes_tested"] is True

    def test_authority_refused(self):
        _, summary = p32_2_gate.run_gate()
        assert summary["authority_claims_refused"] is True


# --- Route decision ----------------------------------------------------------

class TestRouteDecision:
    def test_route_to_model(self):
        registry = builtin_registry()
        req = create_route_request(request_id="r1", task_type="code", requested_role="coder")
        dec = route_to_model(req, registry)
        assert dec["state"] == "ROUTED"
        assert dec["selected_role"] == "coder"
        assert dec["routing_is_advisory"] is True
        assert dec["model_selection_is_not_authority"] is True

    def test_no_model_available(self):
        req = create_route_request(request_id="r2", task_type="code", requested_role="coder")
        dec = route_to_model(req, [])
        assert dec["state"] == "REFUSED"
        assert dec["selected_model_id"] is None

    def test_refuse_authority(self):
        req = create_route_request(request_id="r3", task_type="auth", requested_role="planner")
        ref = refuse_authority_claim(req)
        assert ref["state"] == "REFUSED"
        assert "model_selection_is_not_authority" in ref["reason"]

    def test_invalid_role(self):
        with pytest.raises(ModelRoutingBoundaryError):
            create_route_request(request_id="r4", task_type="code", requested_role="agi_god")

    def test_all_roles_routable(self):
        registry = builtin_registry()
        for role in sorted(MODEL_ROLES):
            req = create_route_request(request_id=f"all-{role}", task_type="test", requested_role=role)
            dec = route_to_model(req, registry)
            assert dec["state"] == "ROUTED", f"role {role} not routable"

    def test_decision_has_hash(self):
        registry = builtin_registry()
        req = create_route_request(request_id="h1", task_type="test", requested_role="planner")
        dec = route_to_model(req, registry)
        assert "decision_hash" in dec


# --- Gate validator -----------------------------------------------------------

class TestGateValidator:
    def _summary(self, **overrides):
        data = {
            "p32_1_green": True,
            "routes_tested": True,
            "refusals_tested": True,
            "authority_claims_refused": True,
            "routing_is_advisory": True,
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
        result = validate_p32_2_gate(self._summary())
        assert result["ok"] is True

    def test_missing_p32_1_fails(self):
        result = validate_p32_2_gate(self._summary(p32_1_green=False))
        assert result["ok"] is False

    def test_no_routes_fails(self):
        result = validate_p32_2_gate(self._summary(routes_tested=False))
        assert result["ok"] is False
