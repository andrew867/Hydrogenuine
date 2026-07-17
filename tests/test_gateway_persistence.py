"""
Test plan: Gateway Persistence (01_gateway_persistence)
- Unit: CRUD for chats/messages/approvals/agents
- Integration: create state, restart server (new store instance), state remains
- Migration: schema create and version bump migration works
"""

import os
import tempfile
import pytest

from hg_gateway.store import InMemoryStore, get_store, MessageRow
from hg_gateway.store_sqlite import SQLiteStore
from hg_gateway import store as store_module
from hg_gateway.db import get_connection, _migrate, _migrate_v25_chat_archive, SCHEMA_VERSION


# Pack3: all store methods take tenant_id first (default "default")
T = "default"


# ---- Unit: InMemoryStore CRUD ----
def test_in_memory_chat_crud():
    s = InMemoryStore()
    assert s.chat_list(T) == []
    cid = s.chat_create(T, title="Test")
    assert cid
    assert len(s.chat_list(T)) == 1
    assert s.chat_get(T, cid)["title"] == "Test"
    assert s.chat_update(T, cid, "Updated") is True
    assert s.chat_get(T, cid)["title"] == "Updated"
    assert s.chat_delete(T, cid) is True
    assert s.chat_get(T, cid) is None
    assert s.chat_delete(T, "nonexistent") is False


def test_in_memory_message_add_and_list():
    s = InMemoryStore()
    cid = s.chat_create(T, title="Chat")
    row = s.message_add(T, cid, "user", "Hello")
    assert isinstance(row, MessageRow)
    assert row.role == "user"
    assert row.content == "Hello"
    msgs = s.message_list(T, cid)
    assert len(msgs) == 1
    assert msgs[0]["content"] == "Hello"


def test_in_memory_agent_upsert_and_list():
    s = InMemoryStore()
    cid = s.chat_create(T, title="Chat")
    s.agent_upsert(T, cid, "a1", "Agent 1", "idle")
    s.agent_upsert(T, cid, "a1", "Agent 1", "working")
    agents = s.agent_list(T, cid)
    assert len(agents) == 1
    assert agents[0]["status"] == "working"


def test_in_memory_approval_add_resolve_and_list():
    s = InMemoryStore()
    aid = s.approval_add(T, "tool", "Title", "Summary", "low", "user1", {"k": "v"}, chat_id="c1")
    assert aid
    pending = s.approval_list(T)
    assert len(pending) == 1
    assert pending[0]["status"] == "pending"
    assert s.approval_resolve(T, aid, "approved", note="ok") is True
    assert len(s.approval_list(T)) == 0


# ---- Unit: SQLiteStore CRUD ----
@pytest.fixture
def sqlite_store(tmp_path):
    path = str(tmp_path / "gateway.sqlite3")
    return SQLiteStore(db_path=path)


def test_sqlite_chat_crud(sqlite_store):
    assert sqlite_store.chat_list(T) == []
    cid = sqlite_store.chat_create(T, title="Test")
    assert cid
    assert len(sqlite_store.chat_list(T)) == 1
    assert sqlite_store.chat_get(T, cid)["title"] == "Test"
    assert sqlite_store.chat_update(T, cid, "Updated") is True
    assert sqlite_store.chat_get(T, cid)["title"] == "Updated"
    assert sqlite_store.chat_delete(T, cid) is True
    assert sqlite_store.chat_get(T, cid) is None


def test_sqlite_message_add_and_list(sqlite_store):
    cid = sqlite_store.chat_create(T, title="Chat")
    row = sqlite_store.message_add(T, cid, "user", "Hello", agent_id="a1")
    assert row.message_id
    msgs = sqlite_store.message_list(T, cid)
    assert len(msgs) == 1
    assert msgs[0]["content"] == "Hello"
    assert msgs[0].get("agent_id") == "a1"


def test_sqlite_approval_add_resolve_and_list(sqlite_store):
    cid = sqlite_store.chat_create(T, title="Chat")
    aid = sqlite_store.approval_add(T, "tool", "T", "S", "low", "u1", {"x": 1}, chat_id=cid)
    assert aid
    assert len(sqlite_store.approval_list(T)) == 1
    assert sqlite_store.approval_resolve(T, aid, "denied", note="nope") is True
    assert len(sqlite_store.approval_list(T)) == 0


def test_sqlite_event_append_and_list(sqlite_store):
    cid = sqlite_store.chat_create(T, title="Chat")
    sqlite_store.event_append(T, cid, "message.delta", {"delta": "hi"})
    sqlite_store.event_append(T, cid, "message.final", {"content": "hi"})
    events = sqlite_store.event_list(T, cid)
    assert len(events) == 2
    assert events[0]["event_type"] == "message.delta"
    assert events[0]["payload"]["delta"] == "hi"


def test_sqlite_chat_list_repairs_broken_assistant_fallback_titles(sqlite_store):
    cid = sqlite_store.chat_create(T, title="I don’t have access to real-time weather data. You might want to check a")
    sqlite_store.message_add(T, cid, "user", "Can you check the weather in five provinces and summarize it?")
    chats = sqlite_store.chat_list(T)
    assert chats[0]["chat_id"] == cid
    assert chats[0]["title"] == "Can you check the weather in five provinces and summa..."
    assert sqlite_store.chat_get(T, cid)["title"] == "Can you check the weather in five provinces and summa..."


# ---- Integration: restart retains state ----
def test_sqlite_persistence_across_restart(tmp_path):
    path = str(tmp_path / "gateway.sqlite3")
    s1 = SQLiteStore(db_path=path)
    cid = s1.chat_create(T, title="Survive")
    s1.message_add(T, cid, "user", "Before restart")
    s1.agent_upsert(T, cid, "a1", "A", "idle")
    aid = s1.approval_add(T, "x", "T", "S", "low", "u", {}, chat_id=cid)

    # Simulate restart: new store instance, same path
    s2 = SQLiteStore(db_path=path)
    assert s2.chat_get(T, cid) is not None
    assert s2.chat_get(T, cid)["title"] == "Survive"
    msgs = s2.message_list(T, cid)
    assert len(msgs) == 1
    assert msgs[0]["content"] == "Before restart"
    agents = s2.agent_list(T, cid)
    assert len(agents) == 1
    s2.approval_resolve(T, aid, "approved")
    assert len(s2.approval_list(T)) == 0


# ---- Migration ----
def test_migration_schema_version(tmp_path):
    path = str(tmp_path / "gateway.sqlite3")
    with get_connection(path) as conn:
        _migrate(conn)
    with get_connection(path) as conn:
        row = conn.execute("SELECT MAX(version) FROM _schema_version").fetchone()
        assert row is not None
        assert row[0] == SCHEMA_VERSION


def test_migration_creates_tables(tmp_path):
    path = str(tmp_path / "gateway.sqlite3")
    with get_connection(path) as conn:
        pass
    with get_connection(path) as conn:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        assert "_schema_version" in tables
        assert "chats" in tables
        assert "messages" in tables
        assert "approvals" in tables
        assert "events" in tables
        assert "principals" in tables


def test_migration_v25_insert_is_idempotent(tmp_path):
    path = str(tmp_path / "gateway.sqlite3")
    import sqlite3
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS _schema_version (
               version INTEGER NOT NULL PRIMARY KEY,
               applied_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS chats (
               chat_id TEXT PRIMARY KEY,
               title TEXT NOT NULL,
               updated_at TEXT NOT NULL,
               unread_count INTEGER NOT NULL DEFAULT 0,
               tenant_id TEXT NOT NULL DEFAULT 'default'
            )"""
        )
        conn.execute("INSERT INTO _schema_version (version, applied_at) VALUES (24, datetime('now'))")
        _migrate_v25_chat_archive(conn)
        conn.execute(
            "INSERT OR IGNORE INTO _schema_version (version, applied_at) VALUES (25, datetime('now'))"
        )
        conn.commit()
        _migrate(conn)
        versions = [row[0] for row in conn.execute("SELECT version FROM _schema_version WHERE version = 25").fetchall()]
        assert versions == [25]
    finally:
        conn.close()


# ---- get_store env ----
def test_get_store_sqlite_backend(tmp_path):
    path = str(tmp_path / "gateway.sqlite3")
    os.environ["HG_GATEWAY_STORE"] = "sqlite"
    os.environ["HG_GATEWAY_DB_PATH"] = path
    try:
        store_module._store = None
        s = get_store()
        assert isinstance(s, SQLiteStore)
        cid = s.chat_create(T, title="Env")
        assert s.chat_get(T, cid)["title"] == "Env"
    finally:
        store_module._store = None
        os.environ.pop("HG_GATEWAY_STORE", None)
        os.environ.pop("HG_GATEWAY_DB_PATH", None)


def test_get_store_sqlite_default(tmp_path):
    """With no env set, default backend is sqlite; needs HG_GATEWAY_DB_PATH for path (or uses default)."""
    store_module._store = None
    prev_store = os.environ.get("HG_GATEWAY_STORE")
    prev_path = os.environ.get("HG_GATEWAY_DB_PATH")
    os.environ.pop("HG_GATEWAY_STORE", None)
    os.environ["HG_GATEWAY_DB_PATH"] = str(tmp_path / "gateway.sqlite3")
    try:
        s = get_store()
        assert isinstance(s, SQLiteStore)
    finally:
        store_module._store = None
        if prev_store is not None:
            os.environ["HG_GATEWAY_STORE"] = prev_store
        else:
            os.environ.pop("HG_GATEWAY_STORE", None)
        if prev_path is not None:
            os.environ["HG_GATEWAY_DB_PATH"] = prev_path
        else:
            os.environ.pop("HG_GATEWAY_DB_PATH", None)


def test_get_store_memory_when_explicit():
    """When HG_GATEWAY_STORE=memory, get_store() returns InMemoryStore."""
    store_module._store = None
    os.environ["HG_GATEWAY_STORE"] = "memory"
    try:
        s = get_store()
        assert isinstance(s, InMemoryStore)
    finally:
        store_module._store = None
        os.environ.pop("HG_GATEWAY_STORE", None)
