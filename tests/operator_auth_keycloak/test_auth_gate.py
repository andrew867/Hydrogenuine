"""Mission cases 27-31: the auth gate must fail closed."""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "operator_auth_keycloak_gate",
    WORKSPACE / "scripts" / "evals" / "operator_auth_keycloak_gate.py")
gate = importlib.util.module_from_spec(_spec)
sys.modules["operator_auth_keycloak_gate"] = gate
_spec.loader.exec_module(gate)


@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    root = tmp_path_factory.mktemp("auth_gate")
    result = gate.run_gate(output_root=root)
    assert result["verdict"] == "GREEN_OPERATOR_AUTH_KEYCLOAK"
    return Path(result["bundle"])


def _copy(bundle: Path, tmp_path: Path) -> Path:
    dest = tmp_path / bundle.name
    shutil.copytree(bundle, dest)
    return dest


def test_gate_fails_if_raw_token_appears(bundle, tmp_path):
    broken = _copy(bundle, tmp_path)
    f = broken / "approval_receipt_keycloak.json"
    payload = json.loads(f.read_text(encoding="utf-8"))
    payload["reason"] = "eyJhbGciOiJSUzI1NiIsImtpZCI6IngifQ.eyJzdWIiOiJ4In0.sig"
    f.write_text(json.dumps(payload), encoding="utf-8")
    verdict = gate.evaluate_bundle(broken)
    assert not verdict["ok"]
    assert any("raw_token" in x or "checksum" in x for x in verdict["failures"])


def test_gate_fails_if_production_auth_claimed_without_keycloak(bundle, tmp_path):
    broken = _copy(bundle, tmp_path)
    f = broken / "approval_receipt_demo_local.json"
    payload = json.loads(f.read_text(encoding="utf-8"))
    payload["operator_identity"]["production_operator_auth"] = True
    f.write_text(json.dumps(payload), encoding="utf-8")
    verdict = gate.evaluate_bundle(broken)
    assert not verdict["ok"]
    assert any("demo_local_claims_production_auth" in x or "checksum" in x
               for x in verdict["failures"])


def test_gate_fails_if_service_role_approves(bundle, tmp_path):
    broken = _copy(bundle, tmp_path)
    f = broken / "gate_result.json"
    payload = json.loads(f.read_text(encoding="utf-8"))
    payload["service_role_blocked"] = False
    f.write_text(json.dumps(payload), encoding="utf-8")
    verdict = gate.evaluate_bundle(broken)
    assert not verdict["ok"]
    assert any("service_role" in x or "checksum" in x for x in verdict["failures"])


def test_gate_fails_if_hardware_auth_claimed(bundle, tmp_path):
    broken = _copy(bundle, tmp_path)
    f = broken / "hardware_auth_disposition.json"
    payload = json.loads(f.read_text(encoding="utf-8"))
    payload["webauthn_hardware_tested"] = True
    f.write_text(json.dumps(payload), encoding="utf-8")
    verdict = gate.evaluate_bundle(broken)
    assert not verdict["ok"]
    assert any("hardware_auth_claimed" in x or "checksum" in x
               for x in verdict["failures"])


def test_gate_writes_result_outside_sealed_bundle(tmp_path):
    external = tmp_path / "external" / "auth_result.json"
    result = gate.run_gate(output_root=tmp_path / "bundle_root", write_result=external)
    assert external.exists()
    assert result["verdict"] == "GREEN_OPERATOR_AUTH_KEYCLOAK"
    assert Path(result["bundle"]) not in external.parents


def test_evaluate_bundle_green_on_intact(bundle):
    verdict = gate.evaluate_bundle(bundle)
    assert verdict["ok"], verdict["failures"]
