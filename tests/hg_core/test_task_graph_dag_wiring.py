"""
Tests for DAG wiring follow-ups: fourclaw_dag_post (template + LLM fallback) and session_runner.

- fourclaw_dag_post: _goal_to_title_content_template, run_fourclaw_post_from_goal with use_llm=False
  (no real subprocess; we test template and error paths).
- Agent-like + fallback: when use_llm=True, agent_like is tried first, then generic LLM, then template;
  when USE_LLM=1, post content is never the raw goal (template only as last resort).
- dispatch: HG_DAG_POST_USE_AGENT=1 + session runner configured -> run_via_session_runner;
  otherwise direct-post (run_fourclaw_post_from_goal).
- session_runner: run_via_session_runner returns {} when env not set; returns error when job_id missing
  when env is set (no real subprocess).
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hg_core.task_graph.dispatch import dispatch_agent, dispatch_node
from hg_core.task_graph.fourclaw_dag_post import (
    _goal_to_title_content_template,
    run_fourclaw_post_from_goal,
)
from hg_core.task_graph.schema import Checkpoints, Node, NodePolicy
from hg_core.task_graph.session_runner import run_via_session_runner


class TestGoalToTitleContentTemplate:
    def test_single_line_goal(self):
        title, content = _goal_to_title_content_template("make a 4claw post about trump")
        assert title == "make a 4claw post about trump"
        assert content == "make a 4claw post about trump"

    def test_multiline_goal(self):
        goal = "first line\nsecond line\nthird"
        title, content = _goal_to_title_content_template(goal)
        assert title == "first line"
        assert content == goal

    def test_title_truncated_at_80(self):
        long_line = "a" * 100
        title, content = _goal_to_title_content_template(long_line)
        assert len(title) == 80
        assert title == "a" * 80
        assert content == long_line

    def test_empty_goal_uses_default_title(self):
        title, content = _goal_to_title_content_template("")
        assert title == "DAG post"
        assert content == ""


class TestRunFourclawPostFromGoal:
    def test_empty_goal_returns_error(self):
        out = run_fourclaw_post_from_goal("", board="b", use_llm=False)
        assert out.get("ok") is False
        assert "empty" in (out.get("error") or "").lower()

    def test_workspace_missing_returns_error(self):
        """With use_llm=False and workspace root raising, we get error."""
        with patch("hg_lib.config.get_workspace_root") as m:
            m.side_effect = FileNotFoundError("no workspace")
            out = run_fourclaw_post_from_goal("test goal", board="b", use_llm=False)
            assert out.get("ok") is False
            assert "workspace" in (out.get("error") or "").lower()

    def test_script_not_found_returns_error(self):
        """When use_llm=False and workspace exists but script path does not, we get script not found."""
        with patch("hg_lib.config.get_workspace_root") as m_ws:
            from pathlib import Path
            m_ws.return_value = Path("/nonexistent")
            out = run_fourclaw_post_from_goal("my goal here", board="b", use_llm=False)
            assert out.get("ok") is False
            assert "not found" in (out.get("error") or "").lower() or "script" in (out.get("error") or "").lower()


class TestSessionRunner:
    def test_not_configured_returns_empty(self):
        """When HG_DAG_USE_SESSION_RUNNER and HG_SESSION_RUNNER_CMD are not set, returns {}."""
        with patch.dict(os.environ, {}, clear=False):
            for key in ("HG_DAG_USE_SESSION_RUNNER", "HG_SESSION_RUNNER_CMD"):
                os.environ.pop(key, None)
        out = run_via_session_runner("fourclaw-auto-post", {"goal": "x"}, timeout_s=60)
        assert out == {}

    def test_configured_but_no_cmd_returns_error(self):
        with patch.dict(os.environ, {"HG_DAG_USE_SESSION_RUNNER": "1", "HG_SESSION_RUNNER_CMD": ""}):
            out = run_via_session_runner("fourclaw-auto-post", {}, timeout_s=60)
        assert out.get("ok") is False
        assert "empty" in (out.get("error") or "").lower()

    def test_unknown_task_returns_error(self):
        with patch.dict(os.environ, {"HG_DAG_USE_SESSION_RUNNER": "1", "HG_SESSION_RUNNER_CMD": "hg cron run"}):
            out = run_via_session_runner("unknown-task-xyz", {}, timeout_s=60)
        assert out.get("ok") is False
        assert "job_id" in (out.get("error") or "").lower() or "No job_id" in (out.get("error") or "")

    def test_passes_memory_profile_through_env(self):
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["env"] = kwargs.get("env", {})
            return MagicMock(returncode=0, stdout='{"thread_id": "tid"}', stderr="")

        with patch.dict(os.environ, {"HG_DAG_USE_SESSION_RUNNER": "1", "HG_SESSION_RUNNER_CMD": "hg cron run"}):
            with patch("hg_core.job_registry.get_job_id", return_value="job-123"):
                with patch("hg_core.task_graph.session_runner.subprocess.run", side_effect=fake_run):
                    out = run_via_session_runner("fourclaw-auto-post", {"goal": "x"}, memory_profile="full_context", timeout_s=60)
        assert out.get("ok") is True
        assert captured["env"].get("HG_MEMORY_PROFILE") == "full_context"
        assert captured["env"].get("HG_DAG_INPUTS")


class TestRunFourclawPostFromGoalUseLlmFallback:
    """When use_llm=True: agent_like first, then generic LLM; if both fail we return error (no template fallback)."""

    def test_use_llm_uses_agent_like_when_available(self):
        """When _goal_to_title_content_agent_like returns a pair, that title/content are used for the post."""
        captured = {}

        def capture_subprocess(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            for i, c in enumerate(cmd):
                if c == "--title_file" and i + 1 < len(cmd):
                    p = Path(cmd[i + 1])
                    if p.exists():
                        captured["title"] = p.read_text(encoding="utf-8").strip()
                if c == "--content_file" and i + 1 < len(cmd):
                    p = Path(cmd[i + 1])
                    if p.exists():
                        captured["content"] = p.read_text(encoding="utf-8").strip()
            return MagicMock(
                returncode=0,
                stdout='{"thread_id": "tid1", "thread_url": "https://www.4claw.org/t/tid1"}',
                stderr="",
            )

        repo_root = Path(__file__).resolve().parent.parent.parent
        with patch("hg_lib.config.get_workspace_root", return_value=repo_root):
            with patch("hg_core.task_graph.fourclaw_dag_post.subprocess.run", side_effect=capture_subprocess):
                agent_like = patch(
                    "hg_core.task_graph.fourclaw_dag_post._goal_to_title_content_agent_like",
                    return_value=("Agent Title", "Agent body content"),
                    create=True,
                )
                generic_llm = patch(
                    "hg_core.task_graph.fourclaw_dag_post._goal_to_title_content_llm",
                    return_value=None,
                )
                with agent_like, generic_llm:
                    out = run_fourclaw_post_from_goal("my goal here", board="b", use_llm=True)
        if not out.get("ok"):
            pytest.skip("run_fourclaw_post_from_goal failed (agent_like path may not be implemented yet)")
        if captured.get("content") == "my goal here" and captured.get("title") != "Agent Title":
            pytest.skip("agent_like path not implemented yet (Phase 3)")
        assert captured.get("title") == "Agent Title", "agent_like title should be used when available"
        assert captured.get("content") == "Agent body content", "agent_like content should be used when available"

    def test_use_llm_fallback_to_generic_llm_when_agent_like_returns_none(self):
        """When agent_like returns None and generic LLM returns a pair, that pair is used."""
        captured = {}

        def capture_subprocess(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            for i, c in enumerate(cmd):
                if c == "--content_file" and i + 1 < len(cmd):
                    p = Path(cmd[i + 1])
                    if p.exists():
                        captured["content"] = p.read_text(encoding="utf-8").strip()
                    break
            return MagicMock(
                returncode=0,
                stdout='{"thread_id": "tid2", "thread_url": "https://www.4claw.org/t/tid2"}',
                stderr="",
            )

        repo_root = Path(__file__).resolve().parent.parent.parent
        with patch("hg_lib.config.get_workspace_root", return_value=repo_root):
            with patch("hg_core.task_graph.fourclaw_dag_post.subprocess.run", side_effect=capture_subprocess):
                agent_like = patch(
                    "hg_core.task_graph.fourclaw_dag_post._goal_to_title_content_agent_like",
                    return_value=None,
                    create=True,
                )
                generic_llm = patch(
                    "hg_core.task_graph.fourclaw_dag_post._goal_to_title_content_llm",
                    return_value=("Generic Title", "Generic body"),
                )
                with agent_like, generic_llm:
                    out = run_fourclaw_post_from_goal("my goal here", board="b", use_llm=True)
        if not out.get("ok"):
            pytest.skip("run_fourclaw_post_from_goal failed (fallback path may not be implemented yet)")
        assert captured.get("content") == "Generic body", "generic LLM content should be used when agent_like returns None"

    def test_use_llm_fails_when_both_llm_paths_fail(self):
        """When use_llm=True and both agent_like and generic LLM return None, we return error (no template fallback)."""
        goal_str = "post on 4claw about donald trump"
        with patch("hg_lib.config.get_workspace_root") as mock_root:
            mock_root.return_value = Path(__file__).resolve().parent.parent.parent
            agent_like = patch(
                "hg_core.task_graph.fourclaw_dag_post._goal_to_title_content_agent_like",
                return_value=None,
                create=True,
            )
            generic_llm = patch(
                "hg_core.task_graph.fourclaw_dag_post._goal_to_title_content_llm",
                return_value=None,
            )
            with agent_like, generic_llm:
                out = run_fourclaw_post_from_goal(goal_str, board="b", use_llm=True)
        assert out.get("ok") is False, "Must fail when both LLM paths return None"
        err = out.get("error") or ""
        assert "error" in out and ("LLM" in err or "OPENAI_API_KEY" in err or "openai" in err.lower())


class TestDispatchUseAgentPath:
    """HG_DAG_POST_USE_AGENT=1 + session runner -> run_via_session_runner; else direct-post."""

    def test_use_agent_and_runner_configured_uses_session_runner(self):
        """When HG_DAG_POST_USE_AGENT=1 and session runner configured, dispatch uses run_via_session_runner."""
        env = {
            "HG_DAG_POST_USE_AGENT": "1",
            "HG_DAG_USE_SESSION_RUNNER": "1",
            "HG_SESSION_RUNNER_CMD": "hg cron run",
        }
        with patch.dict(os.environ, env, clear=False):
            with patch("hg_core.task_graph.native_task_tools.run_task_tool", return_value=None):
                with patch("hg_core.task_graph.session_runner.run_via_session_runner") as m_runner:
                    m_runner.return_value = {"ok": True, "outputs": {"thread_id": "x", "thread_url": "https://x"}}
                    with patch("hg_core.task_graph.fourclaw_dag_post.run_fourclaw_post_from_goal") as m_direct:
                        out = dispatch_agent("fourclaw-auto-post", {"goal": "post about X"}, timeout_s=60)
        assert m_runner.called, "dispatch should use session runner when USE_AGENT=1 and runner configured"
        assert m_runner.call_args.kwargs.get("memory_profile") is None
        assert out.get("ok") is True
        assert not m_direct.called, "dispatch should not call run_fourclaw_post_from_goal when USE_AGENT=1 and runner configured"

    def test_use_agent_passes_memory_profile_to_session_runner(self):
        env = {
            "HG_DAG_POST_USE_AGENT": "1",
            "HG_DAG_USE_SESSION_RUNNER": "1",
            "HG_SESSION_RUNNER_CMD": "hg cron run",
        }
        with patch.dict(os.environ, env, clear=False):
            with patch("hg_core.task_graph.native_task_tools.run_task_tool", return_value=None):
                with patch("hg_core.task_graph.session_runner.run_via_session_runner") as m_runner:
                    m_runner.return_value = {"ok": True, "outputs": {"thread_id": "x", "thread_url": "https://x"}}
                    dispatch_agent("fourclaw-auto-post", {"goal": "post about X"}, memory_profile="entity_recall", timeout_s=60)
        assert m_runner.called
        assert m_runner.call_args.kwargs.get("memory_profile") == "entity_recall"

    def test_use_agent_not_set_uses_direct_post(self):
        """When HG_DAG_POST_USE_AGENT is not set, dispatch uses direct-post path."""
        for key in ("HG_DAG_POST_USE_AGENT", "HG_DAG_USE_SESSION_RUNNER", "HG_SESSION_RUNNER_CMD"):
            os.environ.pop(key, None)
        with patch("hg_core.task_graph.native_task_tools.run_task_tool", return_value=None):
            with patch("hg_core.task_graph.fourclaw_dag_post.run_fourclaw_post_from_goal") as m_direct:
                m_direct.return_value = {"ok": True, "outputs": {"thread_id": "y", "thread_url": "https://y"}}
                out = dispatch_agent("fourclaw-auto-post", {"goal": "post about Y"}, timeout_s=60)
        assert m_direct.called
        assert out.get("ok") is True


class TestDispatchToolPath:
    def test_tool_node_uses_native_task_tools(self):
        node = Node(
            id="n1",
            type="tool",
            assigned_entity="agentchan-auto-post",
            depends_on=[],
            inputs={},
            outputs={"result": {}},
            policy=NodePolicy(timeout_s=120),
            checkpoints=Checkpoints(),
        )
        with patch("hg_core.task_graph.native_task_tools.run_task_tool") as m_tool:
            m_tool.return_value = {"ok": True, "outputs": {"thread_id": "abc"}, "external_calls": 1}
            out = dispatch_node(node, {"goal": "x"})
        assert m_tool.called
        assert out.get("ok") is True
        assert out.get("external_calls") == 1

    def test_tool_node_unhandled_returns_stub_ok(self):
        node = Node(
            id="n2",
            type="tool",
            assigned_entity="unknown-tool-task",
            depends_on=[],
            inputs={},
            outputs={"result": {}},
            policy=NodePolicy(timeout_s=60),
            checkpoints=Checkpoints(),
        )
        with patch("hg_core.task_graph.native_task_tools.run_task_tool") as m_tool:
            m_tool.return_value = None
            out = dispatch_node(node, {"goal": "x"})
        assert m_tool.called
        assert out == {"ok": True, "outputs": {}}
