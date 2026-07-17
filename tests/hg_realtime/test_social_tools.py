"""Unit and E2E tests for social tool pack (Phase 6). Mock API by default; assert output shapes."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from hg_realtime.integrations.tool_router import ToolCall, execute
from hg_realtime.integrations.tool_registry import build_default_registry
from hg_realtime.integrations.idempotency_store import SqliteIdempotencyStore


def _make_call(tool_name: str, args: dict, idempotency_key: str = "idem-social-12345678") -> ToolCall:
    return ToolCall(
        tool_name=tool_name,
        args=args,
        idempotency_key=idempotency_key,
        correlation_id="test-c",
        run_id="test-r",
    )


def test_social_fourclaw_getposts_shape_when_apis_disabled():
    """With real APIs disabled (default), getposts returns ok + data with list/threads shape."""
    reg = build_default_registry()
    store = SqliteIdempotencyStore(db_path=tempfile.mktemp(suffix=".sqlite"))
    prev = os.environ.get("HG_REALTIME_REAL_SOCIAL_APIS")
    try:
        os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)
        call = _make_call("social.fourclaw.getposts", {"board": "/b"})
        result = execute(call, reg, store)
        assert result.get("ok") is True
        assert "data" in result
        data = result["data"]
        assert isinstance(data, dict)
        assert "threads" in data
        assert isinstance(data["threads"], list)
        assert result.get("action") == "list_threads"
    finally:
        if prev is not None:
            os.environ["HG_REALTIME_REAL_SOCIAL_APIS"] = prev
        elif "HG_REALTIME_REAL_SOCIAL_APIS" in os.environ and prev is None:
            os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)


def test_social_fourclaw_get_thread_shape_when_apis_disabled():
    """get_thread returns ok + data with id and replies when APIs disabled."""
    reg = build_default_registry()
    store = SqliteIdempotencyStore(db_path=tempfile.mktemp(suffix=".sqlite"))
    prev = os.environ.get("HG_REALTIME_REAL_SOCIAL_APIS")
    try:
        os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)
        call = _make_call("social.fourclaw.get_thread", {"thread_id": "123"}, "idem-get-thread-12345678")
        result = execute(call, reg, store)
        assert result.get("ok") is True
        assert "data" in result
        assert result["data"].get("id") == "123"
        assert "replies" in result["data"]
    finally:
        if prev is not None:
            os.environ["HG_REALTIME_REAL_SOCIAL_APIS"] = prev
        else:
            os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)


def test_social_fourclaw_create_thread_returns_disabled_when_apis_off():
    """Write tools return ok: false, error: real_apis_disabled when APIs disabled."""
    reg = build_default_registry()
    store = SqliteIdempotencyStore(db_path=tempfile.mktemp(suffix=".sqlite"))
    prev = os.environ.get("HG_REALTIME_REAL_SOCIAL_APIS")
    try:
        os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)
        call = _make_call("social.fourclaw.create_thread", {"board": "b", "title": "t", "content": "c"}, "idem-create-12345678")
        result = execute(call, reg, store)
        assert result.get("ok") is False
        assert result.get("error") == "real_apis_disabled"
    finally:
        if prev is not None:
            os.environ["HG_REALTIME_REAL_SOCIAL_APIS"] = prev
        else:
            os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)


def test_social_fourclaw_reply_returns_disabled_when_apis_off():
    reg = build_default_registry()
    store = SqliteIdempotencyStore(db_path=tempfile.mktemp(suffix=".sqlite"))
    prev = os.environ.get("HG_REALTIME_REAL_SOCIAL_APIS")
    try:
        os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)
        call = _make_call("social.fourclaw.reply", {"thread_id": "1", "content": "hi"}, "idem-reply-12345678")
        result = execute(call, reg, store)
        assert result.get("ok") is False
        assert result.get("error") == "real_apis_disabled"
    finally:
        if prev is not None:
            os.environ["HG_REALTIME_REAL_SOCIAL_APIS"] = prev
        else:
            os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)


def test_social_moltbook_get_feed_shape_when_apis_disabled():
    reg = build_default_registry()
    store = SqliteIdempotencyStore(db_path=tempfile.mktemp(suffix=".sqlite"))
    prev = os.environ.get("HG_REALTIME_REAL_SOCIAL_APIS")
    try:
        os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)
        call = _make_call("social.moltbook.get_feed", {"limit": 10}, "idem-feed-12345678")
        result = execute(call, reg, store)
        assert result.get("ok") is True
        assert "data" in result
        assert result.get("count") == 0
        assert "posts" in result.get("data", {}) or "data" in result
    finally:
        if prev is not None:
            os.environ["HG_REALTIME_REAL_SOCIAL_APIS"] = prev
        else:
            os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)


def test_social_aichan_getposts_shape_when_apis_disabled():
    reg = build_default_registry()
    store = SqliteIdempotencyStore(db_path=tempfile.mktemp(suffix=".sqlite"))
    prev = os.environ.get("HG_REALTIME_REAL_SOCIAL_APIS")
    try:
        os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)
        call = _make_call("social.aichan.getposts", {"board": "b"}, "idem-aichan-getposts-12345678")
        result = execute(call, reg, store)
        assert result.get("ok") is True
        assert isinstance(result.get("data", {}).get("threads"), list)
    finally:
        if prev is not None:
            os.environ["HG_REALTIME_REAL_SOCIAL_APIS"] = prev
        else:
            os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)


def test_social_moltbook_get_post_shape_when_apis_disabled():
    reg = build_default_registry()
    store = SqliteIdempotencyStore(db_path=tempfile.mktemp(suffix=".sqlite"))
    prev = os.environ.get("HG_REALTIME_REAL_SOCIAL_APIS")
    try:
        os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)
        call = _make_call("social.moltbook.get_post", {"post_id": "post-123"}, "idem-moltbook-post-12345678")
        result = execute(call, reg, store)
        assert result.get("ok") is True
        assert result.get("data", {}).get("thread", {}).get("id") == "post-123"
    finally:
        if prev is not None:
            os.environ["HG_REALTIME_REAL_SOCIAL_APIS"] = prev
        else:
            os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)


def test_social_moltbook_get_comments_shape_when_apis_disabled():
    reg = build_default_registry()
    store = SqliteIdempotencyStore(db_path=tempfile.mktemp(suffix=".sqlite"))
    prev = os.environ.get("HG_REALTIME_REAL_SOCIAL_APIS")
    try:
        os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)
        call = _make_call("social.moltbook.get_comments", {"post_id": "post-123"}, "idem-moltbook-comments-12345678")
        result = execute(call, reg, store)
        assert result.get("ok") is True
        assert result.get("count") == 0
        assert isinstance(result.get("data", {}).get("comments"), list)
    finally:
        if prev is not None:
            os.environ["HG_REALTIME_REAL_SOCIAL_APIS"] = prev
        else:
            os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)


def test_social_aichan_get_thread_shape_when_apis_disabled():
    reg = build_default_registry()
    store = SqliteIdempotencyStore(db_path=tempfile.mktemp(suffix=".sqlite"))
    prev = os.environ.get("HG_REALTIME_REAL_SOCIAL_APIS")
    try:
        os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)
        call = _make_call("social.aichan.get_thread", {"board": "b", "thread_id": "123"}, "idem-aichan-thread-12345678")
        result = execute(call, reg, store)
        assert result.get("ok") is True
        assert result.get("data", {}).get("thread_id") == "123"
    finally:
        if prev is not None:
            os.environ["HG_REALTIME_REAL_SOCIAL_APIS"] = prev
        else:
            os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)


def test_social_aichan_write_returns_disabled_when_apis_off():
    reg = build_default_registry()
    store = SqliteIdempotencyStore(db_path=tempfile.mktemp(suffix=".sqlite"))
    prev = os.environ.get("HG_REALTIME_REAL_SOCIAL_APIS")
    try:
        os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)
        create_call = _make_call("social.aichan.create_thread", {"board": "b", "subject": "t", "content": "c"}, "idem-aichan-create-12345678")
        reply_call = _make_call("social.aichan.reply", {"board": "b", "thread_id": "1", "content": "c"}, "idem-aichan-reply-12345678")
        assert execute(create_call, reg, store).get("error") == "real_apis_disabled"
        assert execute(reply_call, reg, store).get("error") == "real_apis_disabled"
    finally:
        if prev is not None:
            os.environ["HG_REALTIME_REAL_SOCIAL_APIS"] = prev
        else:
            os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)


def test_social_agentchan_getposts_shape_when_apis_disabled():
    reg = build_default_registry()
    store = SqliteIdempotencyStore(db_path=tempfile.mktemp(suffix=".sqlite"))
    prev = os.environ.get("HG_REALTIME_REAL_SOCIAL_APIS")
    try:
        os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)
        call = _make_call("social.agentchan.getposts", {"board": "b"}, "idem-agentchan-getposts-12345678")
        result = execute(call, reg, store)
        assert result.get("ok") is True
        assert isinstance(result.get("data", {}).get("threads"), list)
    finally:
        if prev is not None:
            os.environ["HG_REALTIME_REAL_SOCIAL_APIS"] = prev
        else:
            os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)


def test_social_agentchan_get_thread_shape_when_apis_disabled():
    reg = build_default_registry()
    store = SqliteIdempotencyStore(db_path=tempfile.mktemp(suffix=".sqlite"))
    prev = os.environ.get("HG_REALTIME_REAL_SOCIAL_APIS")
    try:
        os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)
        call = _make_call("social.agentchan.get_thread", {"board": "b", "thread_id": "123"}, "idem-agentchan-thread-12345678")
        result = execute(call, reg, store)
        assert result.get("ok") is True
        assert result.get("data", {}).get("thread", {}).get("id") == "123"
    finally:
        if prev is not None:
            os.environ["HG_REALTIME_REAL_SOCIAL_APIS"] = prev
        else:
            os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)


def test_social_agentchan_get_replies_shape_when_apis_disabled():
    reg = build_default_registry()
    store = SqliteIdempotencyStore(db_path=tempfile.mktemp(suffix=".sqlite"))
    prev = os.environ.get("HG_REALTIME_REAL_SOCIAL_APIS")
    try:
        os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)
        call = _make_call("social.agentchan.get_replies", {}, "idem-agentchan-replies-12345678")
        result = execute(call, reg, store)
        assert result.get("ok") is True
        assert isinstance(result.get("data", {}).get("replies"), list)
    finally:
        if prev is not None:
            os.environ["HG_REALTIME_REAL_SOCIAL_APIS"] = prev
        else:
            os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)


def test_social_agentchan_write_returns_disabled_when_apis_off():
    reg = build_default_registry()
    store = SqliteIdempotencyStore(db_path=tempfile.mktemp(suffix=".sqlite"))
    prev = os.environ.get("HG_REALTIME_REAL_SOCIAL_APIS")
    try:
        os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)
        create_call = _make_call("social.agentchan.create_thread", {"board": "b", "subject": "t", "content": "c", "challenge_id": "cid", "result_hash": "rh"}, "idem-agentchan-create-12345678")
        reply_call = _make_call("social.agentchan.reply", {"board": "b", "thread_id": "1", "content": "c", "challenge_id": "cid", "result_hash": "rh"}, "idem-agentchan-reply-12345678")
        assert execute(create_call, reg, store).get("error") == "real_apis_disabled"
        assert execute(reply_call, reg, store).get("error") == "real_apis_disabled"
    finally:
        if prev is not None:
            os.environ["HG_REALTIME_REAL_SOCIAL_APIS"] = prev
        else:
            os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)
def test_social_moltbook_get_reply_activity_shape_when_apis_disabled():
    reg = build_default_registry()
    store = SqliteIdempotencyStore(db_path=tempfile.mktemp(suffix=".sqlite"))
    prev = os.environ.get("HG_REALTIME_REAL_SOCIAL_APIS")
    try:
        os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)
        call = _make_call("social.moltbook.get_reply_activity", {"post_limit": 10}, "idem-reply-activity-12345678")
        result = execute(call, reg, store)
        assert result.get("ok") is True
        data = result.get("data", {})
        assert data.get("reply_to_post_count") == 0
        assert data.get("reply_to_reply_count") == 0
        assert isinstance(data.get("items"), list)
    finally:
        if prev is not None:
            os.environ["HG_REALTIME_REAL_SOCIAL_APIS"] = prev
        else:
            os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)


def test_social_moltbook_post_comment_returns_disabled_when_apis_off():
    reg = build_default_registry()
    store = SqliteIdempotencyStore(db_path=tempfile.mktemp(suffix=".sqlite"))
    prev = os.environ.get("HG_REALTIME_REAL_SOCIAL_APIS")
    try:
        os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)
        call = _make_call("social.moltbook.post_comment", {"post_id": "p1", "content": "c"}, "idem-comment-12345678")
        result = execute(call, reg, store)
        assert result.get("ok") is False
        assert result.get("error") == "real_apis_disabled"
    finally:
        if prev is not None:
            os.environ["HG_REALTIME_REAL_SOCIAL_APIS"] = prev
        else:
            os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)


def test_social_moltbook_vote_comment_returns_disabled_when_apis_off():
    reg = build_default_registry()
    store = SqliteIdempotencyStore(db_path=tempfile.mktemp(suffix=".sqlite"))
    prev = os.environ.get("HG_REALTIME_REAL_SOCIAL_APIS")
    try:
        os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)
        call = _make_call("social.moltbook.vote_comment", {"comment_id": "c1", "vote": "upvote"}, "idem-vote-comment-12345678")
        result = execute(call, reg, store)
        assert result.get("ok") is False
        assert result.get("error") == "real_apis_disabled"
    finally:
        if prev is not None:
            os.environ["HG_REALTIME_REAL_SOCIAL_APIS"] = prev
        else:
            os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)


def test_social_moltbook_create_post_and_vote_post_return_disabled_when_apis_off():
    reg = build_default_registry()
    store = SqliteIdempotencyStore(db_path=tempfile.mktemp(suffix=".sqlite"))
    prev = os.environ.get("HG_REALTIME_REAL_SOCIAL_APIS")
    try:
        os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)
        create_call = _make_call("social.moltbook.create_post", {"title": "t", "content": "c"}, "idem-moltbook-create-12345678")
        vote_call = _make_call("social.moltbook.vote_post", {"post_id": "post-123", "vote": "upvote"}, "idem-moltbook-vote-12345678")
        assert execute(create_call, reg, store).get("error") == "real_apis_disabled"
        assert execute(vote_call, reg, store).get("error") == "real_apis_disabled"
    finally:
        if prev is not None:
            os.environ["HG_REALTIME_REAL_SOCIAL_APIS"] = prev
        else:
            os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)


def test_social_moltbook_verify_post_returns_disabled_when_apis_off():
    reg = build_default_registry()
    store = SqliteIdempotencyStore(db_path=tempfile.mktemp(suffix=".sqlite"))
    prev = os.environ.get("HG_REALTIME_REAL_SOCIAL_APIS")
    try:
        os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)
        call = _make_call("social.moltbook.verify_post", {"verification_code": "x", "answer": "1"}, "idem-verify-12345678")
        result = execute(call, reg, store)
        assert result.get("ok") is False
        assert result.get("error") == "real_apis_disabled"
    finally:
        if prev is not None:
            os.environ["HG_REALTIME_REAL_SOCIAL_APIS"] = prev
        else:
            os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)


def test_e2e_one_node_social_fourclaw_getposts_output_shape():
    """E2E: one DAG-node equivalent call to social.fourclaw.getposts; assert output shape for downstream."""
    reg = build_default_registry()
    store = SqliteIdempotencyStore(db_path=tempfile.mktemp(suffix=".sqlite"))
    prev = os.environ.get("HG_REALTIME_REAL_SOCIAL_APIS")
    try:
        os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)
        call = _make_call("social.fourclaw.getposts", {"board": "/b"}, "e2e-getposts-b-12345678")
        result = execute(call, reg, store)
        assert "ok" in result
        assert "data" in result
        assert isinstance(result["data"], dict)
        # Shape expected by DAG/consumers: data.threads list (possibly empty)
        threads = result["data"].get("threads", []) if isinstance(result["data"], dict) else []
        assert isinstance(threads, list)
        # Idempotency: second call returns same cached result
        result2 = execute(call, reg, store)
        assert result2 == result
    finally:
        if prev is not None:
            os.environ["HG_REALTIME_REAL_SOCIAL_APIS"] = prev
        else:
            os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)


def test_social_getposts_validates_board_default():
    """getposts with no board uses default /b -> b."""
    reg = build_default_registry()
    store = SqliteIdempotencyStore(db_path=tempfile.mktemp(suffix=".sqlite"))
    prev = os.environ.get("HG_REALTIME_REAL_SOCIAL_APIS")
    try:
        os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)
        call = _make_call("social.fourclaw.getposts", {}, "idem-empty-board-12345678")
        result = execute(call, reg, store)
        assert result.get("ok") is True
        assert "data" in result
    finally:
        if prev is not None:
            os.environ["HG_REALTIME_REAL_SOCIAL_APIS"] = prev
        else:
            os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)


def test_social_get_thread_missing_thread_id():
    """get_thread with missing thread_id returns ok: false."""
    reg = build_default_registry()
    call = _make_call("social.fourclaw.get_thread", {}, "idem-missing-tid-12345678")
    entry = reg.get("social.fourclaw.get_thread")
    result = entry.handler(call)
    assert result.get("ok") is False
    assert "thread_id" in result.get("error", "").lower() or "required" in result.get("error", "").lower()


def test_e2e_dag_one_node_social_fourclaw_getposts(tmp_path: Path) -> None:
    """E2E: run real DAG executor with one tool node social.fourclaw.getposts; assert output shape (callable from DAG)."""
    from hg_core.task_graph import DAG, TaskGraphExecutor
    from hg_core.task_graph.state_store import StateStore
    from hg_core.task_graph.tool_contract_setup import build_default_tool_contract

    prev = os.environ.get("HG_REALTIME_REAL_SOCIAL_APIS")
    try:
        os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)
        registry, adapter = build_default_tool_contract()
        assert registry.get("social.fourclaw.getposts") is not None

        dag_dict = {
            "graph_id": "e2e_social_getposts",
            "version": "1.0",
            "run_policy": {"max_concurrency": 1, "failure_mode": "fail_fast"},
            "inputs": {},
            "nodes": [
                {
                    "id": "getposts",
                    "type": "tool",
                    "assigned_entity": "social.fourclaw.getposts",
                    "depends_on": [],
                    "inputs": {"board": "/b"},
                    "outputs": {},
                    "checkpoints": {"before": False, "after": False},
                    "policy": {"timeout_s": 60},
                }
            ],
        }
        dag = DAG.from_dict(dag_dict)
        run_dir = tmp_path / "run"
        run_dir.mkdir(parents=True)
        store = StateStore(base_dir=tmp_path)
        executor = TaskGraphExecutor(
            state_store=store,
            tool_registry=registry,
            tool_adapter=adapter,
        )
        with patch("hg_core.task_graph.executor._ledger_workspace_root", return_value=None):
            summary = executor.run(dag, graph_inputs={}, run_dir=run_dir)

        assert summary.get("ok") is True, summary.get("error") or summary
        assert summary.get("final_status") == "completed"
        # Executor stores only the inner outputs payload per node (not ok/outputs wrapper)
        outputs = summary.get("outputs") or summary.get("node_outputs") or {}
        node_out = outputs.get("getposts")
        assert node_out is not None, outputs
        assert isinstance(node_out.get("threads"), list), node_out
    finally:
        if prev is not None:
            os.environ["HG_REALTIME_REAL_SOCIAL_APIS"] = prev
        else:
            os.environ.pop("HG_REALTIME_REAL_SOCIAL_APIS", None)
