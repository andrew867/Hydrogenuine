"""
Pack3 Phase 1: Multi-tenant boundaries and redaction tests.

- Unit: store requires tenant_id; redaction redacts API keys and sensitive keys
- Integration: tenant A cannot see tenant B's chats; SSE cross-tenant returns 403
"""

import pytest
from fastapi.testclient import TestClient

from hg_gateway.store import InMemoryStore, get_store
from hg_gateway.main import app
from hg_gateway.auth import verify_api_key, get_tenant_context
from hg_core.tenancy.context import TenantContext
from hg_core.security.redaction import redact_text, redact_json, SENSITIVE_KEYS


# ---- Unit: redaction ----
def test_redact_text_bearer():
    out = redact_text("Authorization: Bearer sk-abc123xyz")
    assert "Bearer" not in out or "[REDACTED]" in out
    assert "sk-abc123xyz" not in out


def test_redact_text_api_key():
    out = redact_text("api_key=sk-abc1234567890")
    assert "sk-abc1234567890" not in out
    assert "[REDACTED]" in out


def test_redact_json_sensitive_keys():
    payload = {"content": "hello", "summary": "secret", "other": "keep"}
    out = redact_json(payload)
    assert out["content"] == "[REDACTED]"
    assert out["summary"] == "[REDACTED]"
    assert out["other"] == "keep"


def test_redact_json_nested():
    payload = {"top": {"payload": "hide me", "label": "ok"}}
    out = redact_json(payload)
    assert out["top"]["payload"] == "[REDACTED]"
    assert out["top"]["label"] == "ok"


# ---- Unit: store tenant isolation ----
def test_chat_list_filtered_by_tenant():
    s = InMemoryStore()
    c1 = s.chat_create("tenant_a", title="A")
    c2 = s.chat_create("tenant_b", title="B")
    list_a = s.chat_list("tenant_a")
    list_b = s.chat_list("tenant_b")
    assert len(list_a) == 1
    assert len(list_b) == 1
    assert list_a[0]["chat_id"] == c1
    assert list_b[0]["chat_id"] == c2


def test_chat_get_returns_none_for_wrong_tenant():
    s = InMemoryStore()
    cid = s.chat_create("tenant_a", title="Only A")
    assert s.chat_get("tenant_a", cid) is not None
    assert s.chat_get("tenant_b", cid) is None


def test_chat_tenant_id():
    s = InMemoryStore()
    cid = s.chat_create("tenant_foo", title="Foo")
    assert s.chat_tenant_id(cid) == "tenant_foo"
    assert s.chat_tenant_id("nonexistent") is None


# ---- Integration: API tenant isolation and 403 ----
@pytest.fixture
def client():
    """Client with auth bypass; tenant from X-Tenant-ID header (no override)."""
    from hg_gateway import store as store_module
    store_module._store = None
    app.dependency_overrides[verify_api_key] = lambda: None
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(verify_api_key, None)


def test_create_chat_with_tenant_header(client):
    r = client.post("/v1/chats", json={"title": "Test"}, headers={"X-Tenant-ID": "acme"})
    assert r.status_code == 200
    chat_id = r.json()["chat_id"]
    r2 = client.get("/v1/chats", headers={"X-Tenant-ID": "acme"})
    assert r2.status_code == 200
    chats = r2.json()["chats"]
    assert any(c["chat_id"] == chat_id for c in chats)


def test_cross_tenant_chat_access_returns_403(client):
    # Create chat as tenant_a
    r = client.post("/v1/chats", json={"title": "A"}, headers={"X-Tenant-ID": "tenant_a"})
    assert r.status_code == 200
    chat_id = r.json()["chat_id"]
    # Access as tenant_b
    r2 = client.get(f"/v1/chats/{chat_id}/messages", headers={"X-Tenant-ID": "tenant_b"})
    assert r2.status_code == 403
    assert "another tenant" in (r2.json().get("detail") or "").lower() or "denied" in (r2.json().get("detail") or "").lower()


def test_same_tenant_sees_chat(client):
    r = client.post("/v1/chats", json={"title": "OK"}, headers={"X-Tenant-ID": "t1"})
    assert r.status_code == 200
    chat_id = r.json()["chat_id"]
    r2 = client.get(f"/v1/chats/{chat_id}/messages", headers={"X-Tenant-ID": "t1"})
    assert r2.status_code == 200
