"""Pack 15.3: Steering store and resolution tests. Uses temp SQLite."""

import os
import tempfile
import pytest

from hg_gateway.steering_store import (
    get_chat_steering_profile_ids,
    get_tenant_default_profile_ids,
    resolve_steering_profiles,
    set_chat_steering_profile_ids,
    set_tenant_default_profile_ids,
    steering_profile_create,
    steering_profile_delete,
    steering_profile_get,
    steering_profile_list,
    steering_profile_update,
)


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    prev = os.environ.get("HG_GATEWAY_DB_PATH")
    os.environ["HG_GATEWAY_DB_PATH"] = path
    try:
        yield path
    finally:
        if prev is not None:
            os.environ["HG_GATEWAY_DB_PATH"] = prev
        else:
            os.environ.pop("HG_GATEWAY_DB_PATH", None)
        try:
            os.unlink(path)
        except Exception:
            pass


def test_steering_profile_create_and_get(temp_db):
    from hg_gateway.db import get_connection
    with get_connection():
        pass  # run migrations
    steering_profile_create(
        profile_id="legal_v1",
        tenant_id="t1",
        type="legal",
        strength=0.7,
        prompt_fragments=["Always cite sources."],
    )
    p = steering_profile_get("legal_v1")
    assert p is not None
    assert p["profile_id"] == "legal_v1"
    assert p["tenant_id"] == "t1"
    assert p["type"] == "legal"
    assert p["strength"] == 0.7
    assert p["prompt_fragments"] == ["Always cite sources."]


def test_steering_profile_list_tenant_and_global(temp_db):
    from hg_gateway.db import get_connection
    with get_connection():
        pass
    steering_profile_create(profile_id="global_p", tenant_id=None, type="safety", strength=0.5)
    steering_profile_create(profile_id="tenant_p", tenant_id="t1", type="brand", strength=0.6)
    profiles = steering_profile_list(tenant_id="t1", include_global=True)
    assert len(profiles) >= 2
    ids = [p["profile_id"] for p in profiles]
    assert "global_p" in ids
    assert "tenant_p" in ids


def test_tenant_default_and_resolution(temp_db):
    from hg_gateway.db import get_connection
    from hg_gateway.store import get_store
    with get_connection():
        pass
    steering_profile_create(profile_id="p1", tenant_id="t1", type="legal", strength=0.5)
    set_tenant_default_profile_ids("t1", ["p1"])
    assert get_tenant_default_profile_ids("t1") == ["p1"]
    resolved = resolve_steering_profiles("t1", chat_id=None)
    assert len(resolved) == 1
    assert resolved[0]["profile_id"] == "p1"


def test_chat_override_resolution(temp_db):
    from hg_gateway.db import get_connection
    with get_connection():
        pass
    steering_profile_create(profile_id="default_p", tenant_id="t1", type="legal", strength=0.5)
    steering_profile_create(profile_id="chat_p", tenant_id="t1", type="privacy", strength=0.8)
    set_tenant_default_profile_ids("t1", ["default_p"])
    # Create a chat so we can set override (use same temp DB via env)
    prev_store = None
    prev_backend = os.environ.get("HG_GATEWAY_STORE")
    try:
        from hg_gateway import store as store_mod
        prev_store = store_mod._store
        os.environ["HG_GATEWAY_STORE"] = "sqlite"
        store_mod._store = None
        store = store_mod.get_store()
        chat_id = store.chat_create("t1", title="Test")
        set_chat_steering_profile_ids("t1", chat_id, ["chat_p"])
        assert get_chat_steering_profile_ids("t1", chat_id) == ["chat_p"]
        resolved = resolve_steering_profiles("t1", chat_id=chat_id)
        assert len(resolved) == 1
        assert resolved[0]["profile_id"] == "chat_p"
        resolved_run = resolve_steering_profiles("t1", chat_id=chat_id, run_override=["default_p"])
        assert len(resolved_run) == 1
        assert resolved_run[0]["profile_id"] == "default_p"
    finally:
        store_mod._store = prev_store
        if prev_backend is not None:
            os.environ["HG_GATEWAY_STORE"] = prev_backend
        else:
            os.environ.pop("HG_GATEWAY_STORE", None)


def test_steering_profile_update_and_delete(temp_db):
    from hg_gateway.db import get_connection
    with get_connection():
        pass
    steering_profile_create(profile_id="upd", tenant_id="t1", type="custom", strength=0.5)
    steering_profile_update("upd", strength=0.9)
    p = steering_profile_get("upd")
    assert p["strength"] == 0.9
    ok = steering_profile_delete("upd")
    assert ok is True
    assert steering_profile_get("upd") is None
