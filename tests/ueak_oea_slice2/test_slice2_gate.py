"""Gate self-tests — the Slice 2 gate must fail closed (mission cases 20-24)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "ueak_oea_slice2_gate", WORKSPACE / "scripts" / "evals" / "ueak_oea_slice2_gate.py")
gate = importlib.util.module_from_spec(_spec)
sys.modules["ueak_oea_slice2_gate"] = gate
_spec.loader.exec_module(gate)


@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    root = tmp_path_factory.mktemp("slice2_gate")
    result = gate.run_gate(output_root=root)
    assert result["verdict"] == "GREEN_UEAK_OEA_SLICE2"
    return Path(result["bundle"])


def _copy_bundle(bundle: Path, tmp_path: Path) -> Path:
    import shutil
    dest = tmp_path / bundle.name
    shutil.copytree(bundle, dest)
    return dest


def test_gate_fails_when_consume_receipt_missing(bundle, tmp_path):
    broken = _copy_bundle(bundle, tmp_path)
    (broken / "permit_consume_receipt.json").unlink()
    verdict = gate.evaluate_bundle(broken)
    assert not verdict["ok"]
    assert any("permit_consume_receipt" in f for f in verdict["failures"])


def test_gate_fails_when_replay_rejection_missing(bundle, tmp_path):
    broken = _copy_bundle(bundle, tmp_path)
    (broken / "replay_rejection_result.json").unlink()
    verdict = gate.evaluate_bundle(broken)
    assert not verdict["ok"]
    assert any("replay_rejection" in f for f in verdict["failures"])


def test_gate_fails_when_real_external_enabled(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_OEA_REAL", "1")
    result = gate.run_gate(output_root=tmp_path / "real_on")
    assert result["verdict"] == "RED_UEAK_OEA_SLICE2"
    assert result["real_external_dispatch_enabled"] is True


def test_gate_fails_on_forbidden_claim(bundle, tmp_path):
    broken = _copy_bundle(bundle, tmp_path)
    summary = broken / "summary_report.md"
    summary.write_text(summary.read_text(encoding="utf-8")
                       + "\n\nLive external dispatch was performed.\n", encoding="utf-8")
    verdict = gate.evaluate_bundle(broken)
    assert not verdict["ok"]
    assert "claim_boundary_violation" in verdict["failures"] \
        or any("checksum" in f for f in verdict["failures"])


def test_gate_writes_result_outside_sealed_bundle(tmp_path):
    external = tmp_path / "external" / "slice2_result.json"
    result = gate.run_gate(output_root=tmp_path / "bundle_root",
                           write_result=external)
    assert external.exists()
    assert result["verdict"] == "GREEN_UEAK_OEA_SLICE2"
    # the external copy lives outside the sealed bundle
    assert Path(result["bundle"]) not in external.parents


def test_evaluate_bundle_green_on_intact(bundle):
    verdict = gate.evaluate_bundle(bundle)
    assert verdict["ok"], verdict["failures"]
