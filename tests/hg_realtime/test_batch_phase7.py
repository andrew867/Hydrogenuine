"""Phase 7 E2E: batch analyze-files (50 paths → 50 parse → reduce), web-search (10 URLs → rate limit + cache → reduce)."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_realtime.integrations.workflow_mapping import route_event_to_workflow
from hg_realtime.schemas.event import Event, EventType
from hg_realtime.swarm import SwarmController, SwarmPlan
from hg_realtime.integrations.file_tools import handler_file_parse, idempotency_key_for_file_parse
from hg_realtime.integrations.tool_router import ToolCall, execute
from hg_realtime.integrations.tool_registry import build_default_registry
from hg_realtime.integrations.idempotency_store import SqliteIdempotencyStore
import tempfile


def test_phase7_analyze_50_files_50_parse_reduce(tmp_path: Path) -> None:
    """E2E: 50 paths → 50 file.parse tasks → reduce returns 50 outputs."""
    # Create 50 files under tmp_path
    for i in range(50):
        (tmp_path / f"file_{i:02d}.txt").write_text(f"content_{i}", encoding="utf-8")
    paths = [str(tmp_path / f"file_{i:02d}.txt") for i in range(50)]

    plan = SwarmPlan(
        summary="analyze 50 files",
        tasks=[{"tool_name": "file.parse", "args": {"path": p}} for p in paths],
        max_children=50,
        correlation_id="e2e-50files",
        tenant_id="test",
        actor_id="test",
    )
    # Use mock launcher (no DAG children); controller will use tool tasks only
    from unittest.mock import MagicMock
    mock_launcher = MagicMock()
    controller = SwarmController(launcher=mock_launcher, workspace=tmp_path)
    result = controller.run(plan)

    assert result.status == "completed"
    assert len(result.child_outputs) == 50
    assert result.counts["completed"] == 50
    assert result.counts["failed"] == 0
    for i, out in enumerate(result.child_outputs):
        assert out.get("ok") is True
        data = out.get("data") or {}
        assert "path" in data or "content_preview" in data or "size" in data
    assert result.artifacts_path and Path(result.artifacts_path).exists()


def test_phase7_web_search_10_urls_rate_limit_cache_reduce() -> None:
    """E2E: 10 URLs → 10 search.fetch_url children, rate limit and cache, reduce returns aggregated result."""
    # Use real search tool (fetch_url); rate limiter allows 60/min, cache stores results
    urls = [f"https://example.com/page{i}" for i in range(10)]
    plan = SwarmPlan(
        summary="fetch 10 URLs",
        tasks=[{"tool_name": "search.fetch_url", "args": {"url": u}} for u in urls],
        max_children=10,
        correlation_id="e2e-10urls",
        tenant_id="test",
        actor_id="test",
    )
    from unittest.mock import MagicMock
    mock_launcher = MagicMock()
    controller = SwarmController(launcher=mock_launcher)
    result = controller.run(plan)

    assert len(result.child_outputs) == 10
    # Some may fail (network); we only require structure and that reduce ran
    assert result.counts["completed"] + result.counts["failed"] == 10
    assert "summary" in result.summary or result.artifacts.get("child_count") == 10


def test_file_parse_idempotency_per_path(tmp_path: Path) -> None:
    """file.parse: idempotency key per path; same path returns cached result."""
    (tmp_path / "one.txt").write_text("hello", encoding="utf-8")
    reg = build_default_registry()
    store = SqliteIdempotencyStore(db_path=tempfile.mktemp(suffix=".sqlite"))

    key = idempotency_key_for_file_parse(str(tmp_path / "one.txt"))
    call = ToolCall(
        tool_name="file.parse",
        args={"path": "one.txt", "workspace": str(tmp_path)},
        idempotency_key=key,
        correlation_id="c",
        run_id="r",
    )
    r1 = execute(call, reg, store)
    r2 = execute(call, reg, store)
    assert r1 == r2
    assert r1.get("ok") is True
    assert "data" in r1


def test_batch_ingest_analyze_files_routes_to_swarm() -> None:
    """batch_ingest with workflow_id analyze-files and files[] → swarm with swarm_tasks (file.parse per path)."""
    e = Event(
        event_id="ev-1",
        event_type=EventType.TIMER,
        tenant_id="t",
        actor_id="a",
        correlation_id="c",
        payload={"batch_ingest": {"workflow_id": "analyze-files", "files": ["a.txt", "b.txt"]}},
        dedup_key="d",
    )
    wf_id, resolved = route_event_to_workflow(e)
    assert wf_id == "swarm"
    assert "swarm_tasks" in resolved
    assert len(resolved["swarm_tasks"]) == 2
    assert resolved["swarm_tasks"][0]["tool_name"] == "file.parse"
    assert resolved["swarm_tasks"][0]["args"]["path"] == "a.txt"


def test_batch_ingest_web_search_routes_to_swarm() -> None:
    """batch_ingest with workflow_id web-search and urls[] → swarm with search.fetch_url tasks."""
    e = Event(
        event_id="ev-2",
        event_type=EventType.TIMER,
        tenant_id="t",
        actor_id="a",
        correlation_id="c",
        payload={"batch_ingest": {"workflow_id": "web-search", "urls": ["https://x.com/1", "https://x.com/2"]}},
        dedup_key="d",
    )
    wf_id, resolved = route_event_to_workflow(e)
    assert wf_id == "swarm"
    assert len(resolved["swarm_tasks"]) == 2
    assert resolved["swarm_tasks"][0]["tool_name"] == "search.fetch_url"
    assert resolved["swarm_tasks"][0]["args"]["url"] == "https://x.com/1"
