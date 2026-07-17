"""Tests for hg_core.session_manager."""

import json
import pytest
from unittest.mock import patch

from hg_gateway.operational_state_ledger import save_operational_json_state
from hg_core.session_manager import (
    load_compacted_memory,
    _estimate_tokens,
    verify_compacted_memory_qa,
    COMPACTED_MEMORY_REQUIRED_KEYS,
    load_session_summary_counts,
)


class TestEstimateTokens:
    """Test _estimate_tokens heuristic."""

    def test_string(self):
        assert _estimate_tokens("hello") >= 1
        assert _estimate_tokens("a" * 40) >= 10

    def test_list(self):
        assert _estimate_tokens(["a", "b"]) >= _estimate_tokens("a") + _estimate_tokens("b")

    def test_dict(self):
        assert _estimate_tokens({"k": "v"}) >= 1


class TestLoadCompactedMemoryMaxTokens:
    """Test that load_compacted_memory respects max_tokens."""

    def test_respects_max_tokens_budget(self):
        # Load with small budget; total content should be capped (approximate)
        memory = load_compacted_memory("automation-moltbook-auto-post", max_tokens=100)
        total = (
            _estimate_tokens(memory.get("posts", []))
            + _estimate_tokens(memory.get("interactions", []))
            + _estimate_tokens(memory.get("recent_activity", []))
            + _estimate_tokens(memory.get("decision_context", []))
            + _estimate_tokens(memory.get("context", {}))
            + _estimate_tokens(memory.get("fts_snippets", []))
        )
        # Truncation keeps total within budget; allow for rounding and context overhead
        assert total <= 250

    def test_returns_fts_snippets_key(self):
        memory = load_compacted_memory("automation-moltbook-auto-post", max_tokens=2000)
        assert "fts_snippets" in memory
        assert isinstance(memory["fts_snippets"], list)

    def test_returns_continuity_notes_key(self, tmp_path, monkeypatch):
        agent_dir = tmp_path / "memory" / "automation" / "automation-test-agent"
        agent_dir.mkdir(parents=True)
        monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
        monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
        from hg_core.temporal_changelog import record_temporal_event
        record_temporal_event(
            title="Storage migration",
            summary="There was a platform interruption during the storage cutover.",
            workspace_root=tmp_path,
            kind="migration",
            severity="high",
            affected_entities=["all"],
            start_at="2026-03-08T00:00:00Z",
        )
        with patch("hg_core.session_manager.get_workspace_root", return_value=tmp_path):
            with patch("hg_core.session_manager.get_automation_memory_dir", return_value=agent_dir):
                memory = load_compacted_memory("automation-test-agent", max_tokens=500)
        assert "continuity_notes" in memory
        assert memory["continuity_notes"]

    def test_merges_compatible_legacy_memory_dirs(self, tmp_path):
        operational_dir = tmp_path / "memory" / "automation" / "automation-fourclaw"
        legacy_dir = tmp_path / "memory" / "automation" / "automation-fourclaw-engage"
        operational_dir.mkdir(parents=True)
        legacy_dir.mkdir(parents=True)
        save_operational_json_state(
            tmp_path,
            state_key="automation:session_memory:automation-fourclaw",
            payload={
                "posts": [{"id": "op-1", "content": "new post"}],
                "interactions": [],
                "context": {"source": "operational"},
            },
        )
        save_operational_json_state(
            tmp_path,
            state_key="automation:session_memory:automation-fourclaw-engage",
            payload={
                "posts": [{"id": "legacy-1", "content": "old reply"}],
                "interactions": [{"timestamp": "2026-03-08T00:00:00Z", "content": "old interaction"}],
                "context": {"legacy_topic": "historical memory"},
            },
        )
        with (
            patch("hg_core.session_manager.get_workspace_root", return_value=tmp_path),
            patch("hg_core.session_manager.get_automation_memory_dir", side_effect=lambda agent_id: tmp_path / "memory" / "automation" / f"automation-{agent_id}"),
        ):
            memory = load_compacted_memory("automation-fourclaw", max_tokens=700)
        post_ids = {str(item.get("id")) for item in memory.get("posts", []) if isinstance(item, dict)}
        assert "op-1" in post_ids
        assert "legacy-1" in post_ids
        assert any("old interaction" in str(item) for item in memory.get("interactions", []))
        assert memory.get("context", {}).get("legacy_topic") == "historical memory"

    def test_load_session_summary_counts_merges_bayman_compatible_lineage(self, tmp_path):
        operational_dir = tmp_path / "memory" / "automation" / "automation-newfoundland-bayman"
        legacy_dir = tmp_path / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-engage"
        operational_dir.mkdir(parents=True)
        legacy_dir.mkdir(parents=True)
        save_operational_json_state(
            tmp_path,
            state_key="automation:session_memory:automation-newfoundland-bayman",
            payload={
                "posts": [{"id": "op-1", "content": "shared post"}],
                "interactions": [],
                "context": {"lineage": "bayman"},
            },
        )
        save_operational_json_state(
            tmp_path,
            state_key="automation:session_memory:automation-newfoundland-bayman-fourclaw-engage",
            payload={
                "posts": [],
                "interactions": [{"id": "int-1", "content": "legacy reply"}],
                "context": {},
            },
        )
        with (
            patch("hg_core.session_manager.get_workspace_root", return_value=tmp_path),
            patch("hg_core.session_manager.get_automation_memory_dir", side_effect=lambda agent_id: tmp_path / "memory" / "automation" / f"automation-{agent_id}"),
        ):
            counts = load_session_summary_counts("automation-newfoundland-bayman-fourclaw-engage")
        assert counts["posts_count"] == 1
        assert counts["interactions_count"] == 1
        assert counts["context_exists"] is True


class TestVerifyCompactedMemoryQa:
    """mc3: Compaction QA — required keys and token drift check."""

    def test_required_keys_present_after_load(self):
        """Compacted memory load returns all required keys; QA passes."""
        result = verify_compacted_memory_qa("automation-moltbook-auto-post", max_tokens=500)
        assert result["missing_keys"] == []
        assert result["ok"] is True
        assert "token_estimate" in result
        assert result["token_in_range"] is True
        assert result["token_estimate"] <= int(500 * 1.2)

    def test_required_keys_defined(self):
        """Required keys match what load_compacted_memory produces."""
        memory = load_compacted_memory("automation-moltbook-auto-post", max_tokens=100)
        for k in COMPACTED_MEMORY_REQUIRED_KEYS:
            assert k in memory
