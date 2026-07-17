from __future__ import annotations

import os

from hg_quantum.config import get_quantum_config, is_enabled, is_shadow_mode


def test_quantum_flags_default_off():
    for comp in ("state_correlation", "symmetry_breaking", "ldpc_verification", "noise_characterization"):
        assert is_enabled(comp) is False


def test_env_override_enabled(monkeypatch):
    monkeypatch.setenv("HG_QUANTUM_LDPC_VERIFICATION_ENABLED", "true")
    assert is_enabled("ldpc_verification") is True


def test_shadow_mode_default_true():
    assert is_shadow_mode("ldpc_verification") is True


def test_get_quantum_config_has_latency_budget():
    cfg = get_quantum_config()
    assert "latency_budget_ms" in cfg
    assert cfg["fallback_on_error"] is True
