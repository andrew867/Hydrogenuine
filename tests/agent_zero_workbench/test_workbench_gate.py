"""Gate self-tests (mission cases 27-31) — the gate must fail closed."""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "agent_zero_workbench_gate",
    WORKSPACE / "scripts" / "evals" / "agent_zero_workbench_gate.py")
gate = importlib.util.module_from_spec(_spec)
sys.modules["agent_zero_workbench_gate"] = gate
_spec.loader.exec_module(gate)


@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    root = tmp_path_factory.mktemp("azw_gate")
    result = gate.run_gate(output_root=root)
    assert result["verdict"] == "GREEN_AGENT_ZERO_WORKBENCH", result["verdict"]
    return Path(result["bundle"])


def _copy(bundle, tmp_path):
    dest = tmp_path / bundle.name
    shutil.copytree(bundle, dest)
    return dest


def _set(bundle, file, key, value):
    f = bundle / file
    p = json.loads(f.read_text(encoding="utf-8"))
    p[key] = value
    f.write_text(json.dumps(p), encoding="utf-8")


def test_gate_fails_if_raw_token_appears(bundle, tmp_path):
    broken = _copy(bundle, tmp_path)
    (broken / "run_creation_result.json").write_text(
        json.dumps({"leak": "eyJhbGciOiJSUzI1NiJ9.body.sig"}), encoding="utf-8")
    v = gate.evaluate_bundle(broken)
    assert not v["ok"]
    assert any("raw_token_in" in f or "checksum" in f for f in v["failures"])


def test_gate_fails_if_external_effects_enabled(bundle, tmp_path):
    broken = _copy(bundle, tmp_path)
    _set(broken, "gate_result.json", "external_effects_enabled", True)
    v = gate.evaluate_bundle(broken)
    assert not v["ok"]
    assert any("external_effects_enabled" in f or "checksum" in f for f in v["failures"])


def test_gate_fails_if_old_ui_import(bundle, tmp_path):
    broken = _copy(bundle, tmp_path)
    _set(broken, "gate_result.json", "new_ux_only", False)
    v = gate.evaluate_bundle(broken)
    assert not v["ok"]
    assert any("new_ux_only" in f or "checksum" in f for f in v["failures"])


def test_gate_fails_if_isolation_broken(bundle, tmp_path):
    broken = _copy(bundle, tmp_path)
    _set(broken, "gate_result.json", "run_isolation_ok", False)
    v = gate.evaluate_bundle(broken)
    assert not v["ok"]


def test_gate_writes_result_outside_sealed_bundle(tmp_path):
    external = tmp_path / "external" / "azw.json"
    r = gate.run_gate(output_root=tmp_path / "bundle_root", write_result=external)
    assert external.exists()
    assert r["verdict"].startswith("GREEN")
    assert Path(r["bundle"]) not in external.parents


def test_evaluate_bundle_green_on_intact(bundle):
    v = gate.evaluate_bundle(bundle)
    assert v["ok"], v["failures"]
