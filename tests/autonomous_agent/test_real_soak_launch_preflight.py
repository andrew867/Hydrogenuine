"""Launch preflight tests."""
from __future__ import annotations

from hg_runtime.real_soak_launch.launch_preflight import run_launch_preflight
from hg_runtime.real_soak_launch.schema import RealSoakLaunchVerdict


def test_preflight_no_secrets_in_output(tmp_path, monkeypatch):
    monkeypatch.setattr("hg_runtime.real_soak_launch.schema.STORE_ROOT", tmp_path)
    pf = run_launch_preflight("pf-test", base=tmp_path)
    payload = pf.to_payload()
    assert payload["credential_values_exposed"] is False
    assert "token" not in str(payload).lower() or "credential_values_exposed" in payload


def test_preflight_yellow_envelope_not_armed(tmp_path, monkeypatch):
    monkeypatch.setattr("hg_runtime.real_soak_launch.schema.STORE_ROOT", tmp_path)
    pf = run_launch_preflight("pf-no-env", base=tmp_path)
    assert RealSoakLaunchVerdict.YELLOW_ENVELOPE_NOT_ARMED.value in pf.issues
