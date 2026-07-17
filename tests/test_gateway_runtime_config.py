import os

import pytest

from hg_gateway.auth import runtime_auth_diagnostics, validate_runtime_auth_config


@pytest.fixture(autouse=True)
def _clean_env():
    keys = [
        "HG_ENV",
        "HG_GATEWAY_DEV",
        "HG_GATEWAY_API_KEY",
        "HG_GATEWAY_ADMIN_KEY",
        "HG_DEV_ALLOW_TENANT_HEADER",
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


def test_validate_runtime_auth_config_allows_demo_defaults():
    os.environ["HG_ENV"] = "Demo"
    os.environ["HG_GATEWAY_API_KEY"] = "demo-api-key"
    os.environ["HG_GATEWAY_ADMIN_KEY"] = "demo-admin-key"
    validate_runtime_auth_config()


def test_validate_runtime_auth_config_rejects_default_keys_in_non_demo():
    os.environ["HG_ENV"] = "Production"
    os.environ["HG_GATEWAY_API_KEY"] = "demo-api-key"
    os.environ["HG_GATEWAY_ADMIN_KEY"] = "demo-admin-key"
    with pytest.raises(RuntimeError):
        validate_runtime_auth_config()


def test_runtime_auth_diagnostics_reports_strict_defaults():
    os.environ["HG_ENV"] = "Production"
    os.environ["HG_GATEWAY_API_KEY"] = "demo-api-key"
    os.environ["HG_GATEWAY_ADMIN_KEY"] = "demo-admin-key"
    data = runtime_auth_diagnostics()
    assert data["strict_auth_required"] is True
    assert data["api_key_uses_default"] is True
    assert data["admin_key_uses_default"] is True
