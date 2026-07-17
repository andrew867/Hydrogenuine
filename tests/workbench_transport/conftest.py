"""Fixtures for the Workbench transport hardening tests.

Reuse the Agent Zero Workbench fixture-JWKS operator tokens (rsa_keys/jwks_file/
mint) so upload + SSE run under the same fail-closed operator boundary. No live
Keycloak; no external effects.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

# Re-export the fixture-JWKS helpers so tests can `from ...conftest import mint`.
from tests.agent_zero_workbench.conftest import (  # noqa: F401
    CLIENT_ID, KID, ISSUER, mint, rsa_keys, jwks_file,
)


@pytest.fixture()
def client(monkeypatch, tmp_path, jwks_file):
    monkeypatch.setenv("HG_GATEWAY_STORE", "memory")
    monkeypatch.setenv("HG_OPERATOR_AUTH_MODE", "keycloak")
    monkeypatch.setenv("HG_OIDC_JWKS_FILE", jwks_file)
    monkeypatch.setenv("KEYCLOAK_URL", "http://localhost:8180")
    monkeypatch.setenv("KEYCLOAK_REALM", "hg")
    monkeypatch.setenv("KEYCLOAK_CLIENT_ID", CLIENT_ID)
    monkeypatch.setenv("HG_WORKBENCH_DIR", str(tmp_path / "wb"))
    monkeypatch.delenv("HG_WORKBENCH_MAX_UPLOAD_BYTES", raising=False)
    import hg_gateway.workbench_routes as wr
    wr._STORE = None  # reset the module-level store for this tmp dir
    from hg_gateway.main import app
    return TestClient(app), tmp_path / "wb"
