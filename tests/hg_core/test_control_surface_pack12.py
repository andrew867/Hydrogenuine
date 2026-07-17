"""
Control Surface Pack 12: Performance/scale — perf targets, stream priority, query budget, cache, search, meta API, loadgen.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hg_core.control_surface import (
    api_meta_cache_stats,
    api_meta_freshness,
    api_meta_query_budget,
    get_cards_feed,
    get_card_detail,
    get_entities,
    explain_block,
)
from hg_core.control_surface.perf_targets import (
    API_READ_P95_MS,
    FUSION_CARD_P95_MS,
    LIVE_VIEW_TTI_SECONDS,
    SEARCH_P95_MS,
)
from hg_core.control_surface.stream_priority import (
    STREAM_PRIORITY_P0,
    STREAM_PRIORITY_P1,
    STREAM_PRIORITY_P2,
    action_to_stream_priority,
    should_drop_event_for_backpressure,
)
from hg_core.control_surface.query_budget import (
    DEFAULT_QUERY_BUDGET,
    consume_budget,
    reset_request_budget,
    set_request_budget,
)
from hg_core.control_surface.cache_layer import (
    get_or_set_fusion,
    get_or_set_explain,
    get_cache_stats,
    invalidate_all,
)
from hg_core.control_surface.search import search


def test_perf_targets_exist() -> None:
    assert LIVE_VIEW_TTI_SECONDS == 2.0
    assert API_READ_P95_MS == 400
    assert FUSION_CARD_P95_MS == 800
    assert SEARCH_P95_MS == 500


def test_stream_priority_p0_never_dropped() -> None:
    # When drop_below is P2 or P1, P0 should not be dropped
    assert should_drop_event_for_backpressure(STREAM_PRIORITY_P0, STREAM_PRIORITY_P2) is False
    assert should_drop_event_for_backpressure(STREAM_PRIORITY_P0, STREAM_PRIORITY_P1) is False
    assert should_drop_event_for_backpressure(STREAM_PRIORITY_P0, STREAM_PRIORITY_P0) is False


def test_stream_priority_p2_dropped_when_drop_below_p2() -> None:
    assert should_drop_event_for_backpressure(STREAM_PRIORITY_P2, STREAM_PRIORITY_P2) is False
    assert should_drop_event_for_backpressure(STREAM_PRIORITY_P2, STREAM_PRIORITY_P1) is True


def test_action_to_stream_priority() -> None:
    assert action_to_stream_priority("ENTITY_PAUSED") == STREAM_PRIORITY_P0
    assert action_to_stream_priority("WORK_ITEM_BLOCKED") == STREAM_PRIORITY_P0
    assert action_to_stream_priority("WORK_ITEM_CREATED") == STREAM_PRIORITY_P1
    assert action_to_stream_priority("UNKNOWN_ACTION") == STREAM_PRIORITY_P2


def test_query_budget_enforced() -> None:
    reset_request_budget()
    set_request_budget(100)
    assert consume_budget(50) is True
    assert consume_budget(50) is True
    assert consume_budget(1) is False
    reset_request_budget()
    assert consume_budget(10) is True


def test_cache_fusion_hit() -> None:
    invalidate_all()
    ws = "test_ws"
    card_id = "drift_abc"
    out = get_or_set_fusion(ws, card_id, lambda: {"card_id": card_id, "score": 0.5})
    assert out["score"] == 0.5
    out2 = get_or_set_fusion(ws, card_id, lambda: {"card_id": card_id, "score": 0.9})
    assert out2["score"] == 0.5
    stats = get_cache_stats()
    assert stats["hits"] >= 1
    assert stats["fusion_entries"] >= 1


def test_cache_explain_hit() -> None:
    invalidate_all()
    ws = "test_ws"
    ref_id = "wi1"
    out = get_or_set_explain(ws, ref_id, lambda: {"ref_id": ref_id, "blocked": False})
    assert out["ref_id"] == ref_id
    out2 = get_or_set_explain(ws, ref_id, lambda: {"ref_id": ref_id, "blocked": True})
    assert out2["blocked"] is False
    stats = get_cache_stats()
    assert stats["explain_entries"] >= 1


def test_pagination_no_unbounded_entities(tmp_path: Path) -> None:
    result = get_entities(tmp_path, limit=50)
    if isinstance(result, dict):
        assert "items" in result
        assert len(result["items"]) <= 50
    else:
        assert isinstance(result, list)
        assert len(result) <= 50


def test_pagination_no_unbounded_cards(tmp_path: Path) -> None:
    cards = get_cards_feed(tmp_path, limit=50)
    assert isinstance(cards, list)
    assert len(cards) <= 50


def test_search_returns_items_and_cursor(tmp_path: Path) -> None:
    reset_request_budget()
    out = search(tmp_path, q="", limit=25)
    assert "items" in out
    assert isinstance(out["items"], list)
    assert len(out["items"]) <= 25
    assert "next_cursor" in out


def test_api_meta_freshness_shape(tmp_path: Path) -> None:
    out = api_meta_freshness(tmp_path)
    assert "last_event_id" in out
    assert "freshness_ts" in out
    assert "stream_healthy" in out


def test_api_meta_cache_stats() -> None:
    out = api_meta_cache_stats()
    assert "fusion_entries" in out
    assert "explain_entries" in out
    assert "hits" in out
    assert "misses" in out
    assert "hit_rate" in out


def test_api_meta_query_budget() -> None:
    out = api_meta_query_budget()
    assert out["default_budget"] == DEFAULT_QUERY_BUDGET
    assert "current_budget" in out
    assert "current_used" in out


def test_loadgen_produces_report(tmp_path: Path) -> None:
    import subprocess
    import sys as _sys
    root = Path(__file__).resolve().parent.parent.parent
    loadgen = root / "scripts" / "loadgen_pack12.py"
    if not loadgen.exists():
        pytest.skip("loadgen script not found")
    result = subprocess.run(
        [_sys.executable, str(loadgen), str(tmp_path), "-n", "2"],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(root),
    )
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "started_ts" in result.stdout or "by_op" in result.stdout
