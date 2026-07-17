"""Gate self-tests (mission cases 24-28) — the gate must fail closed."""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "keycloak_live_roundtrip_gate",
    WORKSPACE / "scripts" / "evals" / "keycloak_live_roundtrip_gate.py")
gate = importlib.util.module_from_spec(_spec)
sys.modules["keycloak_live_roundtrip_gate"] = gate
_spec.loader.exec_module(gate)


@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    # Generate a fresh bundle into a temp root so the self-tests are hermetic and
    # do not depend on a prior committed run.
    root = tmp_path_factory.mktemp("klr_gate")
    result = gate.run_gate(output_root=root)
    assert result["verdict"].startswith(("GREEN", "YELLOW")), result["verdict"]
    return Path(result["bundle"])


def _copy(bundle: Path, tmp_path: Path) -> Path:
    dest = tmp_path / bundle.name
    shutil.copytree(bundle, dest)
    return dest


def _set(bundle: Path, file: str, key: str, value):
    f = bundle / file
    payload = json.loads(f.read_text(encoding="utf-8"))
    payload[key] = value
    f.write_text(json.dumps(payload), encoding="utf-8")


def test_gate_fails_if_raw_token_appears(bundle, tmp_path):
    broken = _copy(bundle, tmp_path)
    (broken / "operator_approval_receipt.json").write_text(
        json.dumps({"leak": "eyJhbGciOiJSUzI1NiJ9.payload.sig"}), encoding="utf-8")
    v = gate.evaluate_bundle(broken)
    assert not v["ok"]
    assert any("raw_token_in" in f or "checksum" in f for f in v["failures"])


def test_gate_fails_if_insecure_decode_flagged(bundle, tmp_path):
    broken = _copy(bundle, tmp_path)
    _set(broken, "gate_result.json", "insecure_decode_operator_path_blocked", False)
    v = gate.evaluate_bundle(broken)
    assert not v["ok"]
    assert any("insecure_decode" in f or "checksum" in f for f in v["failures"])


def test_gate_fails_if_production_auth_unbacked(bundle, tmp_path):
    broken = _copy(bundle, tmp_path)
    _set(broken, "gate_result.json", "demo_local_separated", False)
    v = gate.evaluate_bundle(broken)
    assert not v["ok"]


def test_gate_fails_if_hardware_auth_claimed(bundle, tmp_path):
    broken = _copy(bundle, tmp_path)
    _set(broken, "gate_result.json", "webauthn_hardware_tested", True)
    v = gate.evaluate_bundle(broken)
    assert not v["ok"]
    assert any("hardware_auth_claimed" in f or "checksum" in f for f in v["failures"])


def test_gate_writes_result_outside_sealed_bundle(tmp_path):
    external = tmp_path / "external" / "klr.json"
    r = gate.run_gate(output_root=tmp_path / "bundle_root", write_result=external)
    assert external.exists()
    assert r["verdict"].startswith(("GREEN", "YELLOW"))
    assert Path(r["bundle"]) not in external.parents


def test_evaluate_bundle_ok_on_intact(bundle):
    v = gate.evaluate_bundle(bundle)
    assert v["ok"], v["failures"]
