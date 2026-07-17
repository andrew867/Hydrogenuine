import os

import pytest

from hg_gateway.auth import runtime_safety_diagnostics, validate_runtime_safety_config


@pytest.fixture(autouse=True)
def _clean_env():
    keys = [
        "HG_ENV",
        "HG_GATEWAY_DEV",
        "HG_GATEWAY_API_KEY",
        "HG_GATEWAY_ADMIN_KEY",
    ]
    snapshot = {k: os.environ.get(k) for k in keys}
    for key in keys:
        os.environ.pop(key, None)
    try:
        yield
    finally:
        for key, value in snapshot.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_runtime_safety_allows_demo_mode(monkeypatch):
    os.environ["HG_ENV"] = "Demo"
    monkeypatch.setattr(
        "hg_gateway.auth.runtime_safety_diagnostics",
        lambda: {
            "strict_runtime_safety_required": False,
            "tool_stub_fallback_active": True,
            "ledger_crypto_stub_active": True,
            "tool_runtime": {"build_error": "ignored in demo"},
        },
    )
    validate_runtime_safety_config()


def test_runtime_safety_rejects_stub_tool_fallback_in_production(monkeypatch):
    os.environ["HG_ENV"] = "Production"
    monkeypatch.setattr(
        "hg_gateway.auth.runtime_safety_diagnostics",
        lambda: {
            "strict_runtime_safety_required": True,
            "tool_stub_fallback_active": True,
            "ledger_crypto_stub_active": False,
            "tool_runtime": {"build_error": "tool contract import failed"},
        },
    )
    with pytest.raises(RuntimeError, match="stub tool adapter fallback active"):
        validate_runtime_safety_config()


def test_runtime_safety_rejects_stub_ledger_crypto_in_production(monkeypatch):
    os.environ["HG_ENV"] = "Production"
    monkeypatch.setattr(
        "hg_gateway.auth.runtime_safety_diagnostics",
        lambda: {
            "strict_runtime_safety_required": True,
            "tool_stub_fallback_active": False,
            "ledger_crypto_stub_active": True,
            "tool_runtime": {"build_error": None},
        },
    )
    with pytest.raises(RuntimeError, match="stub ledger crypto"):
        validate_runtime_safety_config()


def test_runtime_safety_diagnostics_reports_expected_shape():
    data = runtime_safety_diagnostics()
    assert "tool_runtime" in data
    assert "tool_stub_fallback_active" in data
    assert "ledger_crypto_mode" in data
    assert "ledger_crypto_stub_active" in data
