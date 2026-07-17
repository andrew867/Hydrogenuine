"""Pack 15.2: Tests for signal computation pipeline — hooks, HG_SIGNALS_ENABLED, time-bounded."""

import os
import tempfile
import pytest

from hg_gateway.signals_pipeline import (
    is_signals_enabled,
    compute_signals,
    run_hook,
)
from hg_gateway.signals_store import signal_events_list


def test_is_signals_enabled_default_off(monkeypatch):
    monkeypatch.delenv("HG_SIGNALS_ENABLED", raising=False)
    assert is_signals_enabled() is False


def test_is_signals_enabled_on(monkeypatch):
    monkeypatch.setenv("HG_SIGNALS_ENABLED", "1")
    assert is_signals_enabled() is True
    monkeypatch.setenv("HG_SIGNALS_ENABLED", "true")
    assert is_signals_enabled() is True


def test_compute_signals_rule_based_empty():
    signals, missing = compute_signals("")
    assert "schema_version" in signals
    assert missing == []


def test_compute_signals_rule_based_with_text():
    signals, missing = compute_signals("hello world")
    assert signals.get("schema_version") == "1.0"
    assert missing == []


def test_compute_signals_rule_based_long_text():
    long_text = "x" * 600
    signals, missing = compute_signals(long_text)
    assert "drift_erosion" in signals
    assert missing == []


def test_compute_signals_rule_based_citation_phrases():
    signals, _ = compute_signals("According to the source: this is a citation.")
    assert "verification_behavior" in signals


def test_run_hook_disabled(monkeypatch):
    monkeypatch.delenv("HG_SIGNALS_ENABLED", raising=False)
    event_id = run_hook("pre_plan", tenant_id="t1", chat_id="c1", direction="in", text="hi")
    assert event_id is None


@pytest.fixture
def temp_db_and_env(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    prev_db = os.environ.get("HG_GATEWAY_DB_PATH")
    prev_sig = os.environ.get("HG_SIGNALS_ENABLED")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", path)
    monkeypatch.setenv("HG_SIGNALS_ENABLED", "1")
    yield path
    monkeypatch.delenv("HG_GATEWAY_DB_PATH", raising=False)
    if prev_db is not None:
        os.environ["HG_GATEWAY_DB_PATH"] = prev_db
    if prev_sig is not None:
        os.environ["HG_SIGNALS_ENABLED"] = prev_sig
    else:
        os.environ.pop("HG_SIGNALS_ENABLED", None)
    try:
        os.unlink(path)
    except Exception:
        pass


def test_run_hook_pre_plan(temp_db_and_env):
    # get_connection() runs migrations on first use (signal_events from v17)
    event_id = run_hook("pre_plan", tenant_id="t1", chat_id="c1", direction="in", text="user said this")
    assert event_id is not None
    events = signal_events_list("t1", chat_id="c1")
    assert len(events) >= 1
    assert events[0]["signals_json"].get("schema_version") == "1.0"


def test_run_hook_post_response(temp_db_and_env):
    event_id = run_hook("post_response", tenant_id="t1", chat_id="c1", turn_id="msg-1", direction="out", text="Assistant reply.")
    assert event_id is not None
    events = signal_events_list("t1", chat_id="c1")
    assert any(e["direction"] == "out" for e in events)


def test_run_hook_pre_tool(temp_db_and_env):
    event_id = run_hook("pre_tool", tenant_id="t1", chat_id="c1", direction="in", text='{"tool": "weather", "inputs": {"city": "NYC"}}', provenance_extra={"tool_name": "weather"})
    assert event_id is not None


def test_run_hook_retrieval_insert(temp_db_and_env):
    event_id = run_hook("retrieval_insert", tenant_id="t1", chat_id="c1", direction="in", text="chunk1\n\nchunk2", provenance_extra={"query": "test", "top_k": 5})
    assert event_id is not None


@pytest.mark.asyncio
async def test_chat_turn_produces_signal_events(temp_db_and_env, monkeypatch):
    """Integration: run_turn with mocked LLM produces at least one signal_event when HG_SIGNALS_ENABLED=1."""
    from hg_gateway import store as store_mod
    from hg_gateway.orchestration import run_turn

    # Use SQLite store with same temp DB so messages and signal_events share DB
    prev_store = store_mod._store
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    store_mod._store = None
    try:
        store = store_mod.get_store()
        tenant_id = "default"
        chat_id = store.chat_create(tenant_id, title="Sig test")
        store.message_add(tenant_id, chat_id, "user", "Hello", agent_id=None)

        async def mock_stream(*, messages, **kwargs):
            yield "Hi there."

        class MockRegistry:
            def stream_complete(self, *args, **kwargs):
                return mock_stream(*args, **kwargs)

        try:
            import hg_llm
            monkeypatch.setattr(hg_llm, "get_default_registry", lambda: MockRegistry())
        except ImportError:
            pytest.skip("hg_llm not installed")
        row = await run_turn(
            tenant_id,
            chat_id,
            agent_id="primary",
            agent_label="Primary",
            messages_for_llm=[{"role": "user", "content": "Hello"}],
            emit=lambda ev, pl: None,
        )
        assert row is not None
        events = signal_events_list(tenant_id, chat_id=chat_id)
        assert len(events) >= 1, "chat turn should produce at least one signal_event (pre_plan or post_response)"
    finally:
        store_mod._store = prev_store
