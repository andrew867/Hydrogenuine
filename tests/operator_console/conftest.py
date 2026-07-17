"""Pytest config for operator_console tests: set env before app is imported."""

import os
import tempfile


def pytest_configure(config):
    """Set HG_* env so operator_console app uses temp dirs when tests import it."""
    os.environ["HG_RUNS_ROOT"] = tempfile.mkdtemp(prefix="oc_runs_")
    os.environ["HG_DB_PATH"] = os.path.join(tempfile.gettempdir(), "oc_test_console.db")
    os.environ["HG_API_KEY"] = "test-api-key"
    os.environ["HG_DISABLE_RUN_DISCOVERY"] = "1"
    # Ch4 product API: role-based keys for RBAC tests
    os.environ["HG_PRODUCT_API_KEY_VIEWER"] = "test-product-viewer"
    os.environ["HG_PRODUCT_API_KEY_OPERATOR"] = "test-product-operator"
    os.environ["HG_PRODUCT_API_KEY_ADMIN"] = "test-product-admin"
