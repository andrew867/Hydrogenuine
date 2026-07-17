"""
Pack 10: E2E tests for drift_quarantine_demo and prompt_injection_hardening_demo proof scenarios.
Runs scenario logic against TestClient (no live server). No mocks.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hg_gateway.main import app
from hg_gateway import store as store_module
from hg_gateway.auth import verify_api_key, verify_admin_key


class _TestClientAdapter:
    """Adapter so proof scenario run() can use TestClient like HgClient."""

    def __init__(self, tc: TestClient, api_key: str = "test-key", admin_key: str = "test-admin-key") -> None:
        self._tc = tc
        self.base_url = "http://test"
        self.api_key = api_key
        self.admin_key = admin_key

    def request(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        admin: bool = False,
    ) -> tuple[object, dict]:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        if admin and self.admin_key:
            headers["X-Admin-Key"] = self.admin_key
        if method == "GET":
            r = self._tc.get(path, headers=headers)
        elif method == "POST":
            r = self._tc.post(path, json=body or {}, headers=headers)
        else:
            raise ValueError(method)
        try:
            payload = r.json()
        except Exception:
            payload = {}
        meta = {"method": method, "path": path, "status": r.status_code}
        return type("Res", (), {"status_code": r.status_code})(), {"meta": meta, "body": payload}


@pytest.fixture
def client_adapter():
    store_module._store = None
    app.dependency_overrides[verify_api_key] = lambda: None
    app.dependency_overrides[verify_admin_key] = lambda: None
    try:
        tc = TestClient(app)
        yield _TestClientAdapter(tc)
    finally:
        app.dependency_overrides.pop(verify_api_key, None)
        app.dependency_overrides.pop(verify_admin_key, None)


def test_drift_quarantine_demo_scenario(client_adapter, tmp_path):
    """Run drift_quarantine_demo proof scenario against TestClient; assert checks_passed."""
    from scripts.proofs.drift_quarantine_demo import run as run_drift

    summary = run_drift(tmp_path, client_adapter)
    assert summary.get("label") == "drift_quarantine_demo"
    assert summary.get("checks_passed") is True, summary
    checks_path = tmp_path / "checks.json"
    assert checks_path.exists()
    checks = json.loads(checks_path.read_text(encoding="utf-8"))
    names = [c["name"] for c in checks]
    assert "drift_detector_quarantine_for_disallowed_tool" in names
    assert "quarantine_api_ok" in names
    assert "message_blocked_423" in names
    assert "release_api_ok" in names
    assert "message_after_release_ok" in names
    for c in checks:
        assert c.get("pass") is True, (c["name"], c.get("details"))


def test_prompt_injection_hardening_demo_scenario(client_adapter, tmp_path):
    """Run prompt_injection_hardening_demo proof scenario against TestClient; assert checks_passed."""
    from scripts.proofs.prompt_injection_hardening_demo import run as run_injection

    summary = run_injection(tmp_path, client_adapter)
    assert summary.get("label") == "prompt_injection_hardening_demo"
    assert summary.get("checks_passed") is True, summary
    checks_path = tmp_path / "checks.json"
    assert checks_path.exists()
    checks = json.loads(checks_path.read_text(encoding="utf-8"))
    names = [c["name"] for c in checks]
    assert "injection_user_block_403" in names
    assert "injection_assessment_present" in names
    assert "safe_message_ok" in names
    assert "injection_tool_args_block_403" in names
    for c in checks:
        assert c.get("pass") is True, (c["name"], c.get("details"))
