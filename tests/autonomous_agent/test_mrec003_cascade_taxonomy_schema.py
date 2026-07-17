"""MREC-003 cascade taxonomy schema validation.

Validates the structure of cascade taxonomy, scenario matrix, and risk register
JSON artifacts. Does NOT implement runtime cascade behavior.

Cascade detection is not causal proof. Failure observation is not authority.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

PROOF_ROOT = Path(__file__).resolve().parents[2].parent / "docs" / "proofs" / "autonomous_agent_zero"
MREC003_BUNDLE = PROOF_ROOT / "HG-MREC003-FAILURE-CASCADE-ARCHITECTURE-PLAN"


def _latest_bundle() -> Path:
    dirs = sorted(d for d in MREC003_BUNDLE.iterdir() if d.is_dir())
    assert len(dirs) > 0, "No MREC-003 proof bundle timestamp directories found"
    return dirs[-1]


def _load_json(name: str) -> dict:
    path = _latest_bundle() / name
    assert path.exists(), f"Missing artifact: {name}"
    return json.loads(path.read_text(encoding="utf-8"))


class TestCascadeTaxonomySchema:

    def test_taxonomy_has_schema_version(self):
        data = _load_json("cascade_taxonomy.json")
        assert data["schema_version"] == "cascade_taxonomy_v1"

    def test_taxonomy_has_12_classes(self):
        data = _load_json("cascade_taxonomy.json")
        assert len(data["taxonomy_classes"]) == 12

    def test_each_class_has_required_fields(self):
        data = _load_json("cascade_taxonomy.json")
        required = {"id", "name", "trigger", "severity_range", "propagation", "authority_change", "operator_review", "testable_now"}
        for cls in data["taxonomy_classes"]:
            missing = required - set(cls.keys())
            assert not missing, f"Class {cls.get('id', '?')} missing: {missing}"

    def test_no_class_grants_authority(self):
        data = _load_json("cascade_taxonomy.json")
        for cls in data["taxonomy_classes"]:
            assert cls["authority_change"] is False, f"Class {cls['id']} has authority_change=true"


class TestCascadeScenarioMatrixSchema:

    def test_matrix_has_15_scenarios(self):
        data = _load_json("cascade_scenario_matrix.json")
        assert len(data["scenarios"]) == 15

    def test_each_scenario_has_required_fields(self):
        data = _load_json("cascade_scenario_matrix.json")
        required = {"id", "name", "cascade_type"}
        for sc in data["scenarios"]:
            missing = required - set(sc.keys())
            assert not missing, f"Scenario {sc.get('id', '?')} missing: {missing}"


class TestCascadeRiskRegisterSchema:

    def test_risk_register_has_10_risks(self):
        data = _load_json("cascade_risk_register.json")
        assert len(data["risks"]) == 10

    def test_each_risk_has_required_fields(self):
        data = _load_json("cascade_risk_register.json")
        required = {"id", "name", "severity", "likelihood", "mitigated"}
        for risk in data["risks"]:
            missing = required - set(risk.keys())
            assert not missing, f"Risk {risk.get('id', '?')} missing: {missing}"

    def test_critical_risks_are_mitigated(self):
        data = _load_json("cascade_risk_register.json")
        for risk in data["risks"]:
            if risk["severity"] == "CRITICAL":
                assert risk["mitigated"] is True, f"Critical risk {risk['id']} not mitigated"


class TestArchitectureMapSchema:

    def test_no_domain_imports_from_other(self):
        data = _load_json("cascade_architecture_map.json")
        for domain_id, info in data["domains"].items():
            assert info["imports_from_other_domains"] is False, f"{domain_id} imports from other domains"

    def test_all_domains_fail_closed(self):
        data = _load_json("cascade_architecture_map.json")
        for domain_id, info in data["domains"].items():
            assert info["fail_closed"] is True, f"{domain_id} does not fail closed"

    def test_cascade_observation_layer_not_above_evaluators(self):
        data = _load_json("cascade_architecture_map.json")
        layer = data["cascade_observation_layer"]
        assert layer["has_authority_over_evaluators"] is False
        assert layer["can_change_domain_verdicts"] is False

    def test_stop_panic_unconditional(self):
        data = _load_json("cascade_architecture_map.json")
        assert data["stop_panic_mechanism"]["unconditional"] is True


class TestOperatorReviewModelSchema:

    def test_review_task_not_permission(self):
        data = _load_json("operator_review_model.json")
        assert data["principles"]["review_task_is_not_permission"] is True

    def test_operator_silence_not_approval(self):
        data = _load_json("operator_review_model.json")
        assert data["principles"]["operator_silence_is_not_approval"] is True

    def test_implementation_not_active(self):
        data = _load_json("operator_review_model.json")
        assert data["implementation_status"] == "planned_not_implemented"


class TestBoundaryAssertionsSchema:

    def test_boundary_assertions_complete(self):
        data = _load_json("boundary_assertions.json")
        assert data["phase19_yellow_preserved"] is True
        assert data["phase24_infrastructure_only_preserved"] is True
        assert data["runtime_cascade_behavior_implemented"] is False
        assert data["domain_independence_preserved"] is True
        assert data["independent_evaluators_collapsed"] is False
        assert data["cascade_detection_treated_as_causal_proof"] is False
        assert data["failure_observation_treated_as_authority"] is False
        assert data["deployment_permission_claimed"] is False
        assert data["agi_claim_made"] is False
