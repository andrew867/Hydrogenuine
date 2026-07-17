"""Tests for hg_core.job_registry."""

import os
from pathlib import Path

import pytest

from hg_core.job_registry import (
    get_registry,
    get_job_info,
    get_session_target,
    get_compatible_agent_ids,
    get_compatible_session_targets,
    get_operational_session_target,
    get_operational_agent_id,
    get_agent_id,
    get_job_id,
    get_model,
    graph_id_to_job_id,
    task_name_for_job_id,
    normalize_to_agent_id,
    get_platform,
    get_mode,
    get_operational_binding,
    list_tasks,
    list_social_media_tasks,
    DEFAULT_REGISTRY,
)
from hg_lib.errors import HydrogenuineError


def test_get_registry_returns_defaults(monkeypatch, tmp_path):
    """get_registry returns DEFAULT_REGISTRY when no override."""
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    import hg_core.job_registry as jr
    jr._registry = None  # reset cache
    reg = get_registry()
    assert "moltbook-auto-post" in reg
    assert reg["moltbook-auto-post"]["platform"] == "moltbook"
    assert reg["moltbook-auto-post"]["mode"] == "auto-post"


def test_graph_id_to_job_id():
    """graph_id_to_job_id maps DAG graph_ids to human-readable job_ids for Telegram."""
    assert graph_id_to_job_id("aichan_auto_post_v1") == "aichan-auto-post"
    assert graph_id_to_job_id("fourclaw_engage_v1") == "fourclaw-engage"
    assert graph_id_to_job_id("knowledge_research_auto_v2") == "knowledge-research-auto-v2"
    assert graph_id_to_job_id("overseer_monitor_v1") == "overseer-monitor"
    assert graph_id_to_job_id("unknown_graph_v99") == "unknown_graph_v99"


def test_get_job_info():
    """get_job_info returns correct entry."""
    info = get_job_info("moltbook-auto-post")
    assert info is not None
    assert info["job_id"] == "moltbook-auto-post"
    assert info["session_target"] == "automation-moltbook-auto-post"


def test_get_session_target():
    """get_session_target returns session_target; task_name alias (e.g. fourclaw-auto-post-cadence) resolves to same session."""
    assert get_session_target("moltbook-auto-post") == "automation-moltbook-auto-post"
    assert get_session_target("fourclaw-auto-post-cadence") == "automation-fourclaw-auto-post"


def test_aichan_post_alias():
    """aichan-post maps to same session as aichan-auto-post (Phase 2)."""
    assert get_session_target("aichan-post") == "automation-aichan-auto-post"
    assert get_job_info("aichan-post") is not None
    assert get_job_info("aichan-post")["session_target"] == "automation-aichan-auto-post"


def test_get_agent_id():
    """get_agent_id returns session_target without automation- prefix."""
    assert get_agent_id("moltbook-auto-post") == "moltbook-auto-post"
    assert get_agent_id("fourclaw-auto-post") == "fourclaw-auto-post"


def test_operational_session_targets_share_platform_memory_for_social_jobs():
    assert get_operational_session_target("fourclaw-auto-post") == "automation-underling-chan"
    assert get_operational_session_target("fourclaw-engage") == "automation-underling-chan"
    assert get_operational_session_target("aichan-engage") == "automation-underling-chan"
    assert get_operational_session_target("newfoundland-bayman-fourclaw-auto-post") == "automation-newfoundland-bayman"
    assert get_operational_session_target("newfoundland-bayman-moltbook-engage") == "automation-newfoundland-bayman"
    assert get_operational_agent_id("fourclaw-auto-post") == "underling-chan"
    assert get_operational_agent_id("newfoundland-bayman-fourclaw-auto-post") == "newfoundland-bayman"
    assert get_operational_agent_id("moltbook-engage") == "moltbook"
    assert get_operational_session_target("overseer-monitor") == "automation-overseer-monitor"


def test_compatible_session_targets_include_operational_and_legacy_social_targets():
    assert get_compatible_session_targets("fourclaw-engage") == [
        "automation-underling-chan",
        "automation-fourclaw-engage",
        "automation-fourclaw-auto-post",
        "automation-fourclaw",
        "automation-agentchan-auto-post",
        "automation-agentchan",
        "automation-agentchan-engage",
        "automation-aichan-auto-post",
        "automation-aichan",
        "automation-aichan-engage",
    ]
    assert get_compatible_agent_ids("fourclaw-engage") == [
        "underling-chan",
        "fourclaw-engage",
        "fourclaw-auto-post",
        "fourclaw",
        "agentchan-auto-post",
        "agentchan",
        "agentchan-engage",
        "aichan-auto-post",
        "aichan",
        "aichan-engage",
    ]
    assert get_compatible_session_targets("moltbook-engage") == [
        "automation-moltbook",
        "automation-moltbook-engage",
    ]
    assert get_compatible_agent_ids("moltbook-engage") == ["moltbook", "moltbook-engage"]


def test_bayman_compatible_session_targets_are_isolated_from_underling_family():
    targets = get_compatible_session_targets("newfoundland-bayman-fourclaw-engage")
    agent_ids = get_compatible_agent_ids("newfoundland-bayman-fourclaw-engage")
    assert targets[0] == "automation-newfoundland-bayman"
    assert "automation-newfoundland-bayman-fourclaw-engage" in targets
    assert "automation-newfoundland-bayman-fourclaw-auto-post" in targets
    assert "automation-newfoundland-bayman-moltbook-auto-post" in targets
    assert "automation-underling-chan" not in targets
    assert "newfoundland-bayman" in agent_ids
    assert "underling-chan" not in agent_ids


def test_operational_binding_reports_bayman_fingerprint_and_namespaces():
    binding = get_operational_binding("newfoundland-bayman-fourclaw-engage")
    assert binding is not None
    assert binding["operational_session_target"] == "automation-newfoundland-bayman"
    assert binding["operational_agent_id"] == "newfoundland-bayman"
    assert binding["operational_family"] == "newfoundland-bayman"
    assert binding["fingerprint_id"] == "newfoundland_bayman_operational"
    assert "automation-underling-chan" not in binding["compatible_session_targets"]


def test_get_job_id():
    """get_job_id returns canonical cron/scheduler job id."""
    assert get_job_id("moltbook-auto-post") == "moltbook-auto-post"
    assert get_job_id("fourclaw-auto-post") == "fourclaw-auto-post"


def test_task_name_for_job_id():
    """task_name_for_job_id maps job_id to task_name."""
    assert task_name_for_job_id("fourclaw-auto-post-cadence") == "fourclaw-auto-post"
    assert task_name_for_job_id("moltbook-auto-post") == "moltbook-auto-post"
    assert task_name_for_job_id("unknown-job") is None


def test_normalize_to_agent_id():
    """normalize_to_agent_id maps job_id to agent_id."""
    assert normalize_to_agent_id("fourclaw-auto-post-cadence") == "fourclaw-auto-post"
    assert normalize_to_agent_id("fourclaw-auto-post") == "fourclaw-auto-post"
    assert normalize_to_agent_id("unknown") == "unknown"


def test_get_platform():
    """get_platform returns platform."""
    assert get_platform("moltbook-auto-post") == "moltbook"
    assert get_platform("overseer-monitor") is None


def test_get_mode():
    """get_mode returns mode."""
    assert get_mode("moltbook-auto-post") == "auto-post"


def test_get_model():
    """get_model returns model hint for moltbook (gemini flash-lite); None for tasks without hint."""
    assert get_model("moltbook-auto-post") == "gemini-2.5-flash-lite"
    assert get_model("moltbook-engage") == "gemini-2.5-flash-lite"
    assert get_model("fourclaw-auto-post") is None


def test_list_tasks():
    """list_tasks returns all task names."""
    tasks = list_tasks()
    assert "moltbook-auto-post" in tasks
    assert "newfoundland-bayman-fourclaw-auto-post" in tasks
    assert "overseer-monitor" in tasks
    assert len(tasks) >= 15


def test_list_social_media_tasks():
    """list_social_media_tasks returns only platform tasks."""
    tasks = list_social_media_tasks()
    assert "moltbook-auto-post" in tasks
    assert "overseer-monitor" not in tasks


def test_valid_override(monkeypatch, tmp_path):
    """Valid override merges correctly."""
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    override_dir = tmp_path / "memory" / "automation"
    override_dir.mkdir(parents=True)
    override_file = override_dir / "job_registry.json"
    override_file.write_text(
        '{"moltbook-auto-post": {"job_id": "moltbook-auto-post", "session_target": "automation-moltbook-auto-post", "platform": "moltbook", "mode": "auto-post"}}',
        encoding="utf-8",
    )
    import hg_core.job_registry as jr
    jr._registry = None
    reg = get_registry()
    assert reg["moltbook-auto-post"]["platform"] == "moltbook"


def test_invalid_override_missing_keys(monkeypatch, tmp_path):
    """Override with missing keys: warn and ignore in non-strict."""
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.delenv("HG_STRICT_REGISTRY", raising=False)
    override_dir = tmp_path / "memory" / "automation"
    override_dir.mkdir(parents=True)
    override_file = override_dir / "job_registry.json"
    override_file.write_text(
        '{"moltbook-auto-post": {"job_id": "moltbook-auto-post"}}',
        encoding="utf-8",
    )
    import hg_core.job_registry as jr
    jr._registry = None
    reg = get_registry()
    # Should keep default (missing keys, entry ignored)
    assert reg["moltbook-auto-post"]["session_target"] == "automation-moltbook-auto-post"


def test_invalid_override_strict_raises(monkeypatch, tmp_path):
    """Override with missing keys in strict mode raises."""
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("HG_STRICT_REGISTRY", "1")
    override_dir = tmp_path / "memory" / "automation"
    override_dir.mkdir(parents=True)
    override_file = override_dir / "job_registry.json"
    override_file.write_text(
        '{"moltbook-auto-post": {"job_id": "moltbook-auto-post"}}',
        encoding="utf-8",
    )
    import hg_core.job_registry as jr
    jr._registry = None
    with pytest.raises(HydrogenuineError):
        get_registry()


def test_unknown_job_in_override_warn(monkeypatch, tmp_path):
    """Unknown job in override: warn and ignore in non-strict."""
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    override_dir = tmp_path / "memory" / "automation"
    override_dir.mkdir(parents=True)
    override_file = override_dir / "job_registry.json"
    override_file.write_text(
        '{"unknown-job-xyz": {"job_id": "x", "session_target": "y", "platform": null, "mode": "utility"}}',
        encoding="utf-8",
    )
    import hg_core.job_registry as jr
    jr._registry = None
    reg = get_registry()
    assert "unknown-job-xyz" not in reg


def test_duplicate_job_id_raises(monkeypatch, tmp_path):
    """Duplicate job_id in override raises."""
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    override_dir = tmp_path / "memory" / "automation"
    override_dir.mkdir(parents=True)
    override_file = override_dir / "job_registry.json"
    override_file.write_text(
        '{"moltbook-engage": {"job_id": "moltbook-auto-post", "session_target": "automation-moltbook-engage", "platform": "moltbook", "mode": "engage"}}',
        encoding="utf-8",
    )
    import hg_core.job_registry as jr
    jr._registry = None
    with pytest.raises(HydrogenuineError):
        get_registry()
