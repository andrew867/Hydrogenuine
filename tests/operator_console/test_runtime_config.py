import importlib
import os

import pytest

from operator_console.server.app.core import config as config_module
from operator_console.server.app.core.config import validate_operator_runtime_config


@pytest.fixture(autouse=True)
def _clean_env():
    keys = [
        "HG_ENV",
        "HG_API_KEY",
        "HG_GATEWAY_API_KEY",
        "HG_GATEWAY_ADMIN_KEY",
        "HG_PRODUCT_API_KEY_ADMIN",
        "HG_CONFIG",
        "SAFE_LOCAL_ONLY",
        "HG_STUB_MODEL",
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


def test_operator_runtime_config_allows_demo_default():
    os.environ["HG_ENV"] = "Demo"
    validate_operator_runtime_config()


def test_operator_runtime_config_reports_safe_local_mode():
    os.environ["HG_ENV"] = "Demo"
    os.environ["SAFE_LOCAL_ONLY"] = "1"
    importlib.reload(config_module)
    try:
        assert config_module.settings.safe_local_only is True
        assert config_module.settings.runtime_mode == "safe-local"
    finally:
        importlib.reload(config_module)


def test_operator_runtime_config_rejects_default_in_production():
    os.environ["HG_ENV"] = "Production"
    os.environ["HG_CONFIG"] = str(__file__) + ".missing"
    with pytest.raises(RuntimeError):
        validate_operator_runtime_config()


def test_operator_runtime_config_accepts_explicit_key_in_production():
    os.environ["HG_ENV"] = "Production"
    os.environ["HG_API_KEY"] = "prod-key-123"
    validate_operator_runtime_config()


def test_product_api_keys_fall_back_to_gateway_admin_and_operator():
    os.environ["HG_GATEWAY_ADMIN_KEY"] = "demo-admin-key"
    os.environ["HG_GATEWAY_API_KEY"] = "demo-api-key"
    importlib.reload(config_module)
    try:
        product_keys = config_module.settings.product_api_keys
        assert product_keys["demo-admin-key"] == "admin"
        assert product_keys["demo-api-key"] == "operator"
    finally:
        importlib.reload(config_module)
