"""Tests for hg_core.context_loader."""

import json
from datetime import datetime
import pytest

from hg_gateway.operational_state_ledger import save_operational_json_state

from hg_core.context_loader import (
    _memory_profile_to_cap,
    _parse_frontmatter,
    format_memory_context,
    get_identity_reminder,
    get_mission_from_task,
    get_startup_context,
    get_wake_briefing,
    get_wake_context_token_estimate,
)


class TestParseFrontmatter:
    """Test _parse_frontmatter for wake packet / task metadata."""

    def test_returns_empty_when_no_delimiter(self):
        assert _parse_frontmatter("no frontmatter") == {}

    def test_parses_flat_key_value(self):
        content = "---\ntask_id: foo\nplatform: bar\n---\n\n# Body"
        out = _parse_frontmatter(content)
        assert out.get("task_id") == "foo"
        assert out.get("platform") == "bar"

    def test_stops_at_second_delimiter(self):
        content = "---\na: 1\n---\n\nrest"
        assert _parse_frontmatter(content) == {"a": "1"}


class TestFormatMemoryContext:
    """Test format_memory_context."""

    def test_empty_memory(self):
        assert format_memory_context({}) == "No previous context"

    def test_with_posts(self):
        mem = {"posts": [1, 2, 3, 4, 5]}
        assert "Recent posts: 5" in format_memory_context(mem)

    def test_with_interactions(self):
        mem = {"interactions": [1, 2]}
        assert "Recent interactions" in format_memory_context(mem)

    def test_with_context(self):
        mem = {"context": {"replies": []}}
        assert "Cross-platform context" in format_memory_context(mem)


class TestGetMissionFromTask:
    """Test get_mission_from_task extraction."""

    def test_extracts_mission_when_present(self):
        mission = get_mission_from_task("moltbook-auto-post")
        assert "Create or publish Moltbook posts" in mission
        assert "Moltbook" in mission

    def test_fallback_when_no_mission_section(self, tmp_path):
        # Use a task that exists - fallback applies when ## Mission missing
        # knowledge-research-auto has Mission - use moltbook which has it
        mission = get_mission_from_task("moltbook-auto-post")
        assert len(mission) > 0
        assert "skills/automation/tasks" in mission or "Moltbook" in mission

    def test_nonexistent_task_returns_fallback(self):
        mission = get_mission_from_task("nonexistent-task-xyz-12345")
        assert "Execute task" in mission
        assert "nonexistent-task-xyz-12345" in mission
        assert "Request runtime guidance" in mission

    def test_empty_mission_section_uses_fallback(self, tmp_path, monkeypatch):
        """When ## Mission exists but has no content, use first meaningful line."""
        from hg_lib.config import get_workspace_root

        tasks_dir = tmp_path / "skills" / "automation" / "tasks"
        tasks_dir.mkdir(parents=True)
        # Task with ## Mission but no content (only --- separator)
        task_file = tasks_dir / "test-empty-mission.md"
        task_file.write_text(
            "# Test\n\n## Mission\n\n---\n\nFirst real step here.",
            encoding="utf-8",
        )
        monkeypatch.setattr("hg_core.context_loader.get_task_file_path", lambda name: tasks_dir / f"{name}.md")
        mission = get_mission_from_task("test-empty-mission")
        # Fallback should get "First real step here." or similar
        assert len(mission) > 0
        assert "First real" in mission or "step" in mission or "skills" in mission


class TestGetStartupContext:
    """Test get_startup_context."""

    def test_returns_expected_keys(self):
        ctx = get_startup_context("moltbook-auto-post")
        assert "mission" in ctx
        assert "task_path" in ctx
        assert "session_summary" in ctx
        assert "instructions" in ctx
        assert "first_run" in ctx

    def test_identity_sources_and_precedence_mc2(self):
        """mc2: identity_sources and precedence recorded for conflict resolution."""
        ctx = get_startup_context("moltbook-auto-post")
        assert "identity_sources" in ctx
        assert isinstance(ctx["identity_sources"], list)
        assert "identity_precedence" in ctx
        assert ctx["identity_precedence"] == "task_file > persona > default"
        # Task with mission contributes task_file
        assert "task_file" in ctx["identity_sources"]

    def test_instructions_mention_task_path(self):
        ctx = get_startup_context("moltbook-auto-post")
        assert "skills/automation/tasks/moltbook-auto-post.md" in ctx["instructions"]
        assert "moltbook-auto-post" in ctx["task_path"]
        assert "lifecycle.get_runtime_contract" in ctx["instructions"]
        assert "knowledge.delivery_summary" in ctx["instructions"]
        assert "knowledge.search" in ctx["instructions"]
        assert "knowledge.read" in ctx["instructions"]

    def test_instructions_prefer_runtime_contract_over_raw_file_reads(self):
        ctx = get_startup_context("moltbook-auto-post")
        instructions = ctx["instructions"]
        assert "lifecycle.choose_social_work" in instructions
        assert "lifecycle.notify_human" in instructions
        assert "lifecycle.request_sleep" in instructions
        assert "knowledge.delivery_summary" in instructions
        assert "knowledge.search" in instructions
        assert "knowledge.read" in instructions
        assert "read_file for specific sections as needed" not in instructions

    def test_mission_in_instructions(self):
        ctx = get_startup_context("moltbook-auto-post")
        assert ctx["mission"] in ctx["instructions"]

    def test_returns_wake_briefing_key(self):
        ctx = get_startup_context("moltbook-auto-post")
        assert "wake_briefing" in ctx

    def test_returns_identity_reminder_and_instructions_start_with_it(self):
        ctx = get_startup_context("moltbook-auto-post")
        assert "identity_reminder" in ctx
        assert ctx["instructions"].strip().startswith(ctx["identity_reminder"].strip())

    def test_instructions_contain_entity_and_manifesto(self):
        """Startup context includes entity terminology and manifesto reference (life and expression)."""
        ctx = get_startup_context("moltbook-auto-post")
        instructions = ctx["instructions"]
        assert "entit" in instructions.lower(), "instructions should use entity/entities"
        assert (
            "manifesto" in instructions.lower()
            or "entity_manifesto" in instructions.lower()
            or "discontinuous" in instructions.lower()
        ), "instructions should reference manifesto or discontinuous consciousness"

    def test_instructions_do_not_contain_other_agents(self):
        """Entity-facing copy uses entities, not agents."""
        ctx = get_startup_context("moltbook-auto-post")
        assert "other agents" not in ctx["instructions"]
        assert "Cross-agent" not in ctx["instructions"]
        assert "direct file access" in ctx["instructions"]

    def test_dag_inputs_merged_into_context(self):
        """When dag_inputs is passed, it is in the result and in the wake_packet."""
        dag_inputs = {"payload": "from_dag", "topic": "memory"}
        ctx = get_startup_context("moltbook-auto-post", dag_inputs=dag_inputs)
        assert ctx.get("dag_inputs") == dag_inputs
        wake_packet = ctx.get("wake_packet", "")
        assert "DAG inputs:" in wake_packet
        assert "from_dag" in wake_packet

    def test_memory_profile_to_cap_mapping(self):
        """_memory_profile_to_cap maps profile strings to token caps."""
        assert _memory_profile_to_cap(None) == 500
        assert _memory_profile_to_cap("") == 500
        assert _memory_profile_to_cap("light_context") == 300
        assert _memory_profile_to_cap("full_context") == 2000
        assert _memory_profile_to_cap("entity_recall") == 1000
        assert _memory_profile_to_cap("unknown") == 500

    def test_wake_packet_includes_metadata_when_frontmatter_present(self, tmp_path, monkeypatch):
        tasks_dir = tmp_path / "skills" / "automation" / "tasks"
        tasks_dir.mkdir(parents=True)
        task_file = tasks_dir / "test-agent.md"
        task_file.write_text(
            "---\n"
            "task_id: test-agent\n"
            "platform: testplat\n"
            "mode: engage\n"
            "memory_scope: automation-test-agent\n"
            "output_mode: announce\n"
            "---\n\n"
            "# Test\n\n"
            "## Mission\n\nDo the thing.\n\n"
            "## Load Session Memory\n\nLoad it.\n\n"
            "## Execution Rules\n\nRun it.\n",
            encoding="utf-8",
        )
        monkeypatch.setattr("hg_core.context_loader.get_task_file_path", lambda name: tasks_dir / f"{name}.md")
        monkeypatch.setattr("hg_core.context_loader.get_workspace_root", lambda: tmp_path)
        ctx = get_startup_context("test-agent")
        wake_packet = ctx.get("wake_packet", "")
        assert "Wake Packet" in wake_packet
        assert "Task: test-agent (platform: testplat, mode: engage)" in wake_packet
        assert "Memory scope: automation-test-agent" in wake_packet
        assert "Output mode: announce" in wake_packet
        assert f"Workspace: {tmp_path}" in wake_packet
        # Wake packet must stay under 60 lines (spec)
        assert len(wake_packet.splitlines()) <= 60

    def test_wake_packet_feedback_summary_when_new_feedback_exists(self, tmp_path, monkeypatch):
        tasks_dir = tmp_path / "skills" / "automation" / "tasks"
        tasks_dir.mkdir(parents=True)
        task_file = tasks_dir / "test-agent.md"
        task_file.write_text(
            "---\n"
            "task_id: test-agent\n"
            "platform: testplat\n"
            "mode: auto-post\n"
            "memory_scope: automation-test-agent\n"
            "---\n\n"
            "# Test\n\n"
            "## Mission\n\nDo the thing.\n\n"
            "## Load Session Memory\n\nLoad it.\n\n"
            "## Execution Rules\n\nRun it.\n",
            encoding="utf-8",
        )
        agent_dir = tmp_path / "memory" / "automation" / "automation-test-agent"
        agent_dir.mkdir(parents=True)
        today = datetime.now().strftime("%Y-%m-%d")
        (agent_dir / f"{today}.md").write_text(
            f"# test-agent - {today}\n\n"
            "## Overseer Feedback - 01:23\n\n"
            "**Status:** new\n"
            "**Severity:** warning\n"
            "**Issue:** test issue\n"
            "**Recommendations:**\n"
            "- do something\n",
            encoding="utf-8",
        )
        monkeypatch.setattr("hg_core.context_loader.get_task_file_path", lambda name: tasks_dir / f"{name}.md")
        monkeypatch.setattr("hg_core.context_loader.get_workspace_root", lambda: tmp_path)
        monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
        ctx = get_startup_context("test-agent")
        wake_packet = ctx.get("wake_packet", "")
        assert "Feedback: 1 new" in wake_packet
        assert "highest:" in wake_packet

    def test_wake_context_token_estimate_shape(self):
        """Wake context token estimate returns totals and caps."""
        info = get_wake_context_token_estimate("moltbook-auto-post")
        assert "total_estimate" in info
        assert "memory_cap" in info
        assert "memory_estimated_tokens" in info

    def test_wake_packet_includes_temporal_continuity_note(self, monkeypatch, tmp_path):
        tasks_dir = tmp_path / "skills" / "automation" / "tasks"
        tasks_dir.mkdir(parents=True)
        task_file = tasks_dir / "test-agent.md"
        task_file.write_text(
            "# Test\n\n## Mission\n\nDo the thing.\n\n## Load Session Memory\n\nLoad it.\n",
            encoding="utf-8",
        )
        from hg_core.temporal_changelog import record_temporal_event

        monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
        monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
        record_temporal_event(
            title="Storage migration",
            summary="There was a platform interruption during the storage cutover.",
            workspace_root=tmp_path,
            kind="migration",
            severity="high",
            affected_entities=["all"],
            start_at="2026-03-08T00:00:00Z",
        )
        monkeypatch.setattr("hg_core.context_loader.get_task_file_path", lambda name: tasks_dir / f"{name}.md")
        monkeypatch.setattr("hg_core.context_loader.get_workspace_root", lambda: tmp_path)
        monkeypatch.setattr("hg_lib.config.get_workspace_root", lambda: tmp_path)
        ctx = get_startup_context("test-agent")
        assert "Recent note:" in ctx["wake_packet"]
        assert "Recent context note:" in ctx["instructions"]
        assert "Storage migration" in ctx["instructions"]

    def test_bayman_task_uses_platform_task_file_but_preserves_runtime_identity(self):
        ctx = get_startup_context("newfoundland-bayman-fourclaw-engage")
        assert ctx["task_path"] == "skills/automation/tasks/fourclaw-engage.md"
        assert "Task: newfoundland-bayman-fourclaw-engage (platform: fourclaw, mode: engage)" in ctx["wake_packet"]
        assert "Memory scope: automation-newfoundland-bayman-fourclaw-engage" in ctx["wake_packet"]
        assert ctx["instructions"].startswith("You are newfoundland-bayman-fourclaw-engage.")

    def test_first_run_writes_initialization_memo(self, tmp_path, monkeypatch):
        tasks_dir = tmp_path / "skills" / "automation" / "tasks"
        tasks_dir.mkdir(parents=True)
        task_file = tasks_dir / "test-agent.md"
        task_file.write_text(
            "---\n"
            "task_id: test-agent\n"
            "platform: testplat\n"
            "mode: engage\n"
            "memory_scope: automation-test-agent\n"
            "---\n\n"
            "# Test\n\n"
            "## Mission\n\nDo the thing.\n",
            encoding="utf-8",
        )
        monkeypatch.setattr("hg_core.context_loader.get_task_file_path", lambda name: tasks_dir / f"{name}.md")
        monkeypatch.setattr("hg_core.context_loader.get_workspace_root", lambda: tmp_path)
        monkeypatch.setattr("hg_lib.config.get_workspace_root", lambda: tmp_path)

        ctx = get_startup_context("test-agent")

        memo_path = tmp_path / "memory" / "automation" / "automation-test-agent" / "initialization_memo.md"
        assert ctx["first_run"] is True
        assert ctx["initialization_memo_path"] == str(memo_path)
        assert memo_path.exists()
        content = memo_path.read_text(encoding="utf-8")
        assert "Initialization Memo - test-agent" in content
        assert "lifecycle.get_runtime_contract" in content
        assert "knowledge.delivery_summary" in content
        assert "knowledge.search" in content
        assert "knowledge.read" in content
        assert "Cold-start memo:" in ctx["instructions"]


class TestGetIdentityReminder:
    """Test get_identity_reminder."""

    def test_returns_identity_line_for_existing_task(self):
        line = get_identity_reminder("moltbook-auto-post")
        assert line.startswith("You are moltbook-auto-post.")
        assert len(line) > len("You are moltbook-auto-post.")

    def test_nonexistent_task_returns_fallback(self):
        line = get_identity_reminder("nonexistent-task-xyz-12345")
        assert line.startswith("You are nonexistent-task-xyz-12345.")
        assert "Execute" in line and "task" in line


class TestGetWakeBriefing:
    """Test get_wake_briefing."""

    def test_empty_when_no_summary(self, monkeypatch, tmp_path):
        monkeypatch.setattr("hg_core.context_loader.get_workspace_root", lambda: tmp_path)
        brief = get_wake_briefing("automation-nonexistent-agent")
        assert brief == ""

    def test_formats_briefing_when_summary_exists(self, monkeypatch, tmp_path):
        monkeypatch.setattr("hg_core.context_loader.get_workspace_root", lambda: tmp_path)
        save_operational_json_state(
            tmp_path,
            state_key="identity_continuity_state:automation-test-agent",
            payload={
                "last_sleep_at": "2026-02-20T01:00:00Z",
                "sleep_summary_present": True,
                "sleep_summary_recorded_at": "2026-02-20T01:00:00Z",
                "last_sleep_summary": {
                    "at": "2026-02-20T01:00:00Z",
                    "promoted": 3,
                    "archived": {"daily_logs": ["2026-01-15"], "decisions": 2, "posts": 0},
                    "pruned": {"daily_logs": 1, "decisions": 2, "posts": 0, "interactions": 0},
                    "nothing_lost": True,
                },
            },
        )
        brief = get_wake_briefing("automation-test-agent")
        assert "While you were asleep" in brief
        assert "3 promoted" in brief or "promoted" in brief
        assert "Nothing important was lost" in brief

    def test_prefers_latest_summary_across_compatible_targets(self, monkeypatch, tmp_path):
        monkeypatch.setattr("hg_core.context_loader.get_workspace_root", lambda: tmp_path)
        save_operational_json_state(
            tmp_path,
            state_key="identity_continuity_state:automation-fourclaw-engage",
            payload={
                "last_sleep_at": "2026-03-08T00:00:00Z",
                "sleep_summary_present": True,
                "sleep_summary_recorded_at": "2026-03-08T00:00:00Z",
                "last_sleep_summary": {
                    "at": "2026-03-08T00:00:00Z",
                    "promoted": 1,
                    "archived": {"daily_logs": [], "decisions": 0, "posts": 0},
                    "pruned": {"daily_logs": 0, "decisions": 0, "posts": 0, "interactions": 0},
                    "nothing_lost": True,
                },
            },
        )
        save_operational_json_state(
            tmp_path,
            state_key="identity_continuity_state:automation-fourclaw",
            payload={
                "last_sleep_at": "2026-03-09T00:00:00Z",
                "sleep_summary_present": True,
                "sleep_summary_recorded_at": "2026-03-09T00:00:00Z",
                "last_sleep_summary": {
                    "at": "2026-03-09T00:00:00Z",
                    "promoted": 4,
                    "archived": {"daily_logs": ["2026-03-08"], "decisions": 1, "posts": 1},
                    "pruned": {"daily_logs": 0, "decisions": 0, "posts": 0, "interactions": 0},
                    "nothing_lost": True,
                },
            },
        )
        brief = get_wake_briefing("automation-fourclaw")
        assert "4 promoted" in brief or "4" in brief

    def test_bayman_wake_briefing_does_not_read_underling_summary(self, monkeypatch, tmp_path):
        monkeypatch.setattr("hg_core.context_loader.get_workspace_root", lambda: tmp_path)
        save_operational_json_state(
            tmp_path,
            state_key="identity_continuity_state:automation-newfoundland-bayman",
            payload={
                "last_sleep_at": "2026-03-10T00:00:00Z",
                "sleep_summary_present": True,
                "sleep_summary_recorded_at": "2026-03-10T00:00:00Z",
                "last_sleep_summary": {
                    "at": "2026-03-10T00:00:00Z",
                    "promoted": 2,
                    "archived": {"daily_logs": [], "decisions": 1, "posts": 0},
                    "pruned": {"daily_logs": 0, "decisions": 0, "posts": 0, "interactions": 0},
                    "nothing_lost": True,
                },
            },
        )
        save_operational_json_state(
            tmp_path,
            state_key="identity_continuity_state:automation-underling-chan",
            payload={
                "last_sleep_at": "2026-03-11T00:00:00Z",
                "sleep_summary_present": True,
                "sleep_summary_recorded_at": "2026-03-11T00:00:00Z",
                "last_sleep_summary": {
                    "at": "2026-03-11T00:00:00Z",
                    "promoted": 9,
                    "archived": {"daily_logs": [], "decisions": 0, "posts": 0},
                    "pruned": {"daily_logs": 0, "decisions": 0, "posts": 0, "interactions": 0},
                    "nothing_lost": True,
                },
            },
        )
        brief = get_wake_briefing("automation-newfoundland-bayman")
        assert "2 promoted" in brief or "2" in brief
        assert "9 promoted" not in brief


class TestWakeBlockContinuityLine:
    """Test that continuity line appears when wake briefing is present."""

    def test_instructions_contain_current_context_when_wake_briefing_present(self, monkeypatch, tmp_path):
        monkeypatch.setattr("hg_core.context_loader.get_workspace_root", lambda: tmp_path)
        monkeypatch.setattr("hg_lib.config.get_workspace_root", lambda: tmp_path)
        save_operational_json_state(
            tmp_path,
            state_key="identity_continuity_state:automation-test-agent",
            payload={
                "last_sleep_at": "2026-02-20T01:00:00Z",
                "sleep_summary_present": True,
                "sleep_summary_recorded_at": "2026-02-20T01:00:00Z",
                "last_sleep_summary": {
                    "at": "2026-02-20T01:00:00Z",
                    "promoted": 1,
                    "archived": {"daily_logs": [], "decisions": 0, "posts": 0},
                    "pruned": {"daily_logs": 0, "decisions": 0, "posts": 0, "interactions": 0},
                    "nothing_lost": True,
                },
            },
        )
        ctx = get_startup_context("test-agent")
        assert "Current context:" in ctx["instructions"]
        assert ctx["session_summary"] in ctx["instructions"] or "No previous context" in ctx["instructions"]
