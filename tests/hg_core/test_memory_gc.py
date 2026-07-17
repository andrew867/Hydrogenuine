"""Tests for hg_core.memory_gc."""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from hg_core.memory_gc import run_gc_for_agent, _ttl_prune_posts
from hg_gateway.shared_storage import append_agent_decision


class TestRunGcForAgent:
    """Test run_gc_for_agent promote/archive/prune."""

    def test_missing_memory_dir_returns_empty_result(self, tmp_path):
        cfg = {"retention_days_daily_logs": 30, "max_decisions": 500, "max_posts": 200, "max_interactions": 500}
        r = run_gc_for_agent("nonexistent-agent", cfg, tmp_path)
        assert r["promoted"] == 0
        assert r["nothing_lost"] is True
        assert r["archived"] == {"daily_logs": [], "decisions": 0, "posts": 0}
        assert r["pruned"] == {"daily_logs": 0, "decisions": 0, "posts": 0, "interactions": 0}
        assert r["errors"] == []

    def test_promote_creates_summary_7d(self, tmp_path):
        agent_id = "test-agent"
        memory_dir = tmp_path / "memory" / "automation" / f"automation-{agent_id}"
        memory_dir.mkdir(parents=True)
        now = datetime.now(timezone.utc)
        day_1 = (now - timedelta(days=2)).strftime("%Y-%m-%d")
        day_2 = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        (memory_dir / f"{day_1}.md").write_text("## Day 18\n\nSome activity.", encoding="utf-8")
        (memory_dir / f"{day_2}.md").write_text("## Day 19\n\nMore activity.", encoding="utf-8")
        cfg = {"retention_days_daily_logs": 30, "max_decisions": 500, "max_posts": 200, "max_interactions": 500}
        r = run_gc_for_agent(agent_id, cfg, tmp_path)
        assert r["promoted"] >= 1
        assert r["errors"] == []
        summary_file = memory_dir / "summary_7d.json"
        assert summary_file.exists()
        data = json.loads(summary_file.read_text(encoding="utf-8"))
        assert "days" in data
        assert len(data["days"]) >= 1

    def test_promote_uses_codec_when_sleep_prep_has_fingerprint(self, tmp_path):
        agent_id = "codec-agent"
        memory_dir = tmp_path / "memory" / "automation" / f"automation-{agent_id}"
        memory_dir.mkdir(parents=True)
        now = datetime.now(timezone.utc)
        day = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        (memory_dir / f"{day}.md").write_text("## Day\n\nSteering session notes.", encoding="utf-8")
        (memory_dir / "sleep_prep.json").write_text(
            json.dumps(
                {
                    "important_sections": [
                        {
                            "source": f"{day}.md",
                            "fingerprint_profile": {
                                "cognitive_fingerprint": {
                                    "analysis_vs_intuition": 0.5,
                                    "quantum_cognitive_profile": {"symmetry_breaking_role": "neutral"},
                                }
                            },
                            "artifact_refs": ["artifact://memory/test"],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        cfg = {
            "retention_days_daily_logs": 30,
            "max_decisions": 500,
            "max_posts": 200,
            "max_interactions": 500,
            "heavy_artifact_consolidation": True,
        }
        run_gc_for_agent(agent_id, cfg, tmp_path)
        data = json.loads((memory_dir / "summary_7d.json").read_text(encoding="utf-8"))
        assert any(d.get("transport") == "codec" for d in data["days"])

    def test_archive_daily_logs_moves_old_files(self, tmp_path):
        agent_id = "test-agent"
        memory_dir = tmp_path / "memory" / "automation" / f"automation-{agent_id}"
        memory_dir.mkdir(parents=True)
        # Old file: 60 days ago
        (memory_dir / "2025-12-20.md").write_text("Old day.", encoding="utf-8")
        cfg = {"retention_days_daily_logs": 30, "max_decisions": 500, "max_posts": 200, "max_interactions": 500}
        r = run_gc_for_agent(agent_id, cfg, tmp_path)
        archive_dir = memory_dir / "archive"
        assert archive_dir.exists()
        assert (archive_dir / "2025-12-20.md").exists()
        assert not (memory_dir / "2025-12-20.md").exists()
        assert len(r["archived"].get("daily_logs", [])) == 1
        assert r["nothing_lost"] is True

    def test_shared_decisions_are_summarized_without_file_archive(self, tmp_path):
        agent_id = "test-agent"
        memory_dir = tmp_path / "memory" / "automation" / f"automation-{agent_id}"
        memory_dir.mkdir(parents=True)
        now = datetime.now(timezone.utc)
        (memory_dir / f"{(now - timedelta(days=1)).strftime('%Y-%m-%d')}.md").write_text("## Day 1\n\nShared ledger test.", encoding="utf-8")
        (memory_dir / f"{(now - timedelta(days=2)).strftime('%Y-%m-%d')}.md").write_text("## Day 2\n\nMore shared ledger test.", encoding="utf-8")
        cfg = {"retention_days_daily_logs": 30, "max_decisions": 500, "max_posts": 200, "max_interactions": 500}
        with (
            patch("hg_lib.config.get_workspace_root", return_value=tmp_path),
            patch.dict("os.environ", {"HG_GATEWAY_STORE": "sqlite", "HG_GATEWAY_DB_PATH": str(tmp_path / "gateway.sqlite3")}, clear=False),
        ):
            for i in range(5):
                append_agent_decision(
                    decision_id=f"decision-{i}",
                    agent_id=agent_id,
                    timestamp=(datetime.now(timezone.utc) - timedelta(minutes=i)).isoformat().replace("+00:00", "Z"),
                    action=f"action_{i}",
                    rationale="shared ledger test",
                    alternatives=[],
                    tradeoffs=None,
                    context="test",
                    outcome=None,
                )
            r = run_gc_for_agent(agent_id, cfg, tmp_path)
            summary = json.loads((memory_dir / "summary_7d.json").read_text(encoding="utf-8"))
        assert r["archived"].get("decisions", 0) == 0
        assert r["pruned"].get("decisions", 0) == 0
        assert summary["decision_count_recent"] == 5
        assert len(summary["days"]) >= 1
        assert r["nothing_lost"] is True

    def test_ttl_prune_posts_summarize_and_drop(self, tmp_path):
        """mc1: Posts older than posts_ttl_days are summarized then removed."""
        agent_id = "ttl-agent"
        memory_dir = tmp_path / "memory" / "automation" / f"automation-{agent_id}"
        memory_dir.mkdir(parents=True)
        archive_dir = memory_dir / "archive"
        now = datetime.now(timezone.utc)
        old_date = (now - timedelta(days=45)).strftime("%Y-%m-%dT%H:%M:%SZ")
        recent_date = (now - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        posts = {
            "posts": [
                {"id": "old1", "created_at": old_date, "text": "Old post one"},
                {"id": "old2", "timestamp": old_date, "content": "Old post two"},
                {"id": "recent", "created_at": recent_date, "text": "Recent post"},
            ]
        }
        (memory_dir / "posts.json").write_text(json.dumps(posts, indent=2), encoding="utf-8")
        config = {"posts_ttl_days": 30, "summarize_before_drop": True}
        pruned, errors = _ttl_prune_posts(memory_dir, archive_dir, config)
        assert pruned == 2
        assert errors == []
        remaining = json.loads((memory_dir / "posts.json").read_text(encoding="utf-8"))
        assert len(remaining["posts"]) == 1
        assert remaining["posts"][0]["id"] == "recent"
        summary_files = list(archive_dir.glob("posts_ttl_summary_*.json"))
        assert len(summary_files) == 1
        summary_data = json.loads(summary_files[0].read_text(encoding="utf-8"))
        assert len(summary_data["summaries"]) == 2
        assert summary_data["ttl_days"] == 30
