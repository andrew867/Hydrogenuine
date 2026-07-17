"""Tool router: validate idempotency_key; execute with idempotency store."""

import pytest

from hg_realtime.integrations.tool_router import ToolCall, ToolRouterEnforcer, execute
from hg_realtime.integrations.tool_registry import ToolRegistry
from hg_realtime.integrations.idempotency_store import SqliteIdempotencyStore


def test_router_rejects_missing_idempotency_key():
    enforcer = ToolRouterEnforcer()
    call = ToolCall(tool_name="x", args={}, idempotency_key="", correlation_id="c", run_id="r")
    with pytest.raises(ValueError, match="idempotency_key"):
        enforcer.validate(call)


def test_router_rejects_short_idempotency_key():
    enforcer = ToolRouterEnforcer()
    call = ToolCall(tool_name="x", args={}, idempotency_key="short", correlation_id="c", run_id="r")
    with pytest.raises(ValueError, match="idempotency_key"):
        enforcer.validate(call)


def test_router_accepts_valid_key():
    enforcer = ToolRouterEnforcer()
    call = ToolCall(tool_name="x", args={}, idempotency_key="a" * 8, correlation_id="c", run_id="r")
    enforcer.validate(call)


def test_execute_same_key_twice_returns_cached():
    import os
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    try:
        store = SqliteIdempotencyStore(db_path=path)
        reg = ToolRegistry()
        call_count = 0
        def handler(call):
            nonlocal call_count
            call_count += 1
            return {"ok": True, "n": call_count}
        reg.register("test.tool", handler)
        call = ToolCall(tool_name="test.tool", args={}, idempotency_key="idem-key-12345678", correlation_id="c", run_id="r")
        r1 = execute(call, reg, store)
        assert r1 == {"ok": True, "n": 1}
        r2 = execute(call, reg, store)
        assert r2 == {"ok": True, "n": 1}
        assert call_count == 1
    finally:
        try:
            os.unlink(path)
        except PermissionError:
            pass
