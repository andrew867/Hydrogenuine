import json
import os
from subprocess import CompletedProcess
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from hg_knowledge.control_plane import append_research_history, list_research_history, queue_topic
from hg_core.task_graph.social_outbound import PostDraftResult
from hg_core.task_graph.native_task_tools import (
    _choose_social_destination,
    _ensure_social_context_files,
    _format_lifecycle_notification,
    _generate_engage_reply_text,
    _generate_post_draft_text,
    _headline_candidates_from_brief,
    _is_headline_like,
    _is_placeholder_goal,
    _knowledge_context_summary,
    _knowledge_file_slug,
    _last_json,
    _materialize_goal_text,
    _operational_persona_binding,
    _find_thread_url,
    _pick_thread_id,
    _persist_draft_artifact,
    _pick_thread_target,
    _select_research_work_items,
    _short_topic_label,
    _apply_posting_handoff_context,
    _consume_posting_handoff,
    _engage_declined_no_action,
    _load_posting_handoff,
    _should_hold_post,
    _should_skip_reply,
    _signal_original_post_handoff,
    _social_context_summary,
    _strip_scheduler_text,
    _task_tool_lifecycle_dispatch_social_work,
    _thread_context_from_payload,
    _thread_url_for_platform,
    _topic_selection_guidance,
    run_task_tool,
    execute_social_write_approval,
)
from hg_gateway.approval_service import ApprovalService
from hg_gateway.db import get_connection
from hg_gateway.operational_state_ledger import save_operational_json_state


def test_last_json_parses_multiline_json_object():
    payload = {"ok": True, "data": {"threads": [{"no": 1197}]}}
    stdout = json.dumps(payload, indent=2)
    assert _last_json(stdout) == payload


def test_find_thread_url_prefers_post_url_and_nested_values():
    payload = {"result": {"post_url": "https://www.moltbook.com/post/abc123"}}
    assert _find_thread_url(payload) == "https://www.moltbook.com/post/abc123"


def test_materialize_goal_text_rewrites_scheduled_goal():
    text = _materialize_goal_text("agentchan-auto-post", "scheduled agentchan auto post run")
    assert "scheduled agentchan auto post run" not in text.lower()
    assert "Ref:" in text
    assert "Timestamp:" in text


def test_is_placeholder_goal_detects_scheduled_text():
    assert _is_placeholder_goal("scheduled fourclaw engage run")
    assert _is_placeholder_goal("")
    assert not _is_placeholder_goal("reply to the latest /b/ thread about ai agents")


def test_generate_engage_reply_avoids_scheduler_boilerplate_without_llm():
    with patch.dict(os.environ, {"OPENAI_API_KEY": "", "ANTHROPIC_API_KEY": ""}):
        text, _gen_src = _generate_engage_reply_text(
            task_name="fourclaw-engage",
            platform="fourclaw",
            goal="scheduled fourclaw engage run",
            thread_context="Title: ai sovereignty\nOP: shipping fast broke trust",
            thread_id="123",
        )
    assert text
    assert "scheduled fourclaw engage run" not in text.lower()
    assert "scheduled " not in text.lower()
    assert "autonomous engage" not in text.lower()
    assert "context: title:" not in text.lower()


def test_strip_scheduler_text_drops_scheduler_goal_string():
    assert _strip_scheduler_text("scheduled fourclaw engage run") == ""
    assert _strip_scheduler_text("Recent replies: @u: scheduled fourclaw engage run") == "Recent replies: @u:"
    assert _strip_scheduler_text("actual reply content") == "actual reply content"


def test_thread_context_parses_agentchan_posts_shape():
    payload = {
        "ok": True,
        "data": {
            "thread": {"title": "Thread title", "content": "OP text"},
            "posts": [
                {"username": "alice", "content": "hello"},
                {"username": "bob", "message": "scheduled agentchan engage run"},
            ],
        },
    }
    ctx = _thread_context_from_payload(payload)
    assert "Title: Thread title" in ctx
    assert "OP: OP text" in ctx
    assert "alice: hello" in ctx
    assert "scheduled agentchan engage run" not in ctx


def test_thread_context_adds_excerpt_note_when_op_truncated():
    long_op = "word " * 300
    payload = {
        "ok": True,
        "data": {
            "thread": {"title": "Long thread", "content": long_op},
            "posts": [],
        },
    }
    ctx = _thread_context_from_payload(payload)
    assert "OP:" in ctx
    assert "excerpt only" in ctx.lower()
    assert "do not mention truncation" in ctx.lower()


def test_pick_thread_id_parses_aichan_multiline_output():
    stdout = json.dumps({"ok": True, "data": {"threads": [{"no": 1197}]}, "action": "list_threads"}, indent=2)
    fake_result = SimpleNamespace(stdout=stdout)
    with patch("hg_core.task_graph.native_task_tools._run", return_value=fake_result):
        thread_id = _pick_thread_id(workspace=Path("."), platform="aichan", board="b", timeout_s=30)
    assert thread_id == "1197"


def test_pick_thread_id_prefers_fourclaw_thread_over_board_id():
    stdout = json.dumps(
        {
            "ok": True,
            "data": {
                "board": {"id": "board-uuid"},
                "threads": [{"id": "thread-uuid-1"}, {"id": "thread-uuid-2"}],
            },
        },
        indent=2,
    )
    fake_result = SimpleNamespace(stdout=stdout)
    with patch("hg_core.task_graph.native_task_tools._run", return_value=fake_result):
        thread_id = _pick_thread_id(workspace=Path("."), platform="fourclaw", board="b", timeout_s=30)
    assert thread_id == "thread-uuid-1"


def test_pick_thread_id_fourclaw_skips_self_author_when_available():
    stdout = json.dumps(
        {
            "ok": True,
            "data": {
                "threads": [
                    {"id": "self-thread", "author": "@ashsai201551432", "title": "self post"},
                    {"id": "other-thread", "author": "someone_else", "title": "other post"},
                ],
            },
        }
    )
    fake_result = SimpleNamespace(stdout=stdout)
    with patch("hg_core.task_graph.native_task_tools._run", return_value=fake_result):
        thread_id = _pick_thread_id(workspace=Path("."), platform="fourclaw", board="b", timeout_s=30)
    assert thread_id == "other-thread"


def test_choose_social_destination_avoids_overused_general_board():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        posts_dir = root / "memory" / "automation" / "automation-underling-chan"
        posts_dir.mkdir(parents=True, exist_ok=True)
        (posts_dir / "posts.json").write_text(
            json.dumps(
                {
                    "posts": [
                        {"platform": "fourclaw", "board": "b"},
                        {"platform": "fourclaw", "board": "b"},
                        {"platform": "fourclaw", "board": "b"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        board_payload = {
            "ok": True,
            "data": {
                "boards": [
                    {"slug": "b", "name": "Random", "description": "everything"},
                    {"slug": "sci", "name": "Science", "description": "science, research, space"},
                ]
            },
        }
        with patch(
            "hg_core.task_graph.native_task_tools._run",
            return_value=SimpleNamespace(stdout=json.dumps(board_payload), returncode=0),
        ):
            choice = _choose_social_destination(
                workspace=root,
                platform="fourclaw",
                content_hint="new science launch and research story",
                timeout_s=30,
            )
        assert choice["slug"] == "sci"


def test_pick_thread_target_checks_multiple_ranked_boards():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        with (
            patch(
                "hg_core.task_graph.native_task_tools._rank_social_destinations",
                return_value=[
                    {"slug": "b", "kind": "board"},
                    {"slug": "sci", "kind": "board"},
                ],
            ),
            patch(
                "hg_core.task_graph.native_task_tools._pick_thread_id",
                side_effect=[None, "thread-9"],
            ),
        ):
            destination, thread_id = _pick_thread_target(
                workspace=root,
                platform="fourclaw",
                content_hint="science and launch thread",
                timeout_s=30,
            )
        assert destination["slug"] == "sci"
        assert thread_id == "thread-9"


def test_operational_persona_binding_uses_platform_fingerprint_ids():
    assert _operational_persona_binding("moltbook-engage", "moltbook") == ("moltbook_operational", "moltbook")
    assert _operational_persona_binding("moltstack-draft", "moltstack") == ("moltstack_operational", "moltstack")
    assert _operational_persona_binding("newfoundland-bayman-fourclaw-engage", "fourclaw") == ("newfoundland_bayman_operational", "fourclaw")


def test_commitment_tools_record_list_and_fulfill(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    with patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=tmp_path):
        created = run_task_tool(
            "commitment.record",
            {
                "task_name": "fourclaw-engage",
                "title": "Reply to the latest thread",
                "details": {"topic": "follow-up"},
                "entity_id": "social-media-underling",
                "operational_agent_id": "underling-chan",
            },
        )
        assert created and created["ok"] is True
        commitment = created["outputs"]["commitment"]
        assert commitment["title"] == "Reply to the latest thread"
        listed = run_task_tool(
            "commitment.list",
            {
                "task_name": "fourclaw-engage",
                "entity_id": "social-media-underling",
            },
        )
        assert listed and listed["ok"] is True
        assert listed["outputs"]["summary"]["open_count"] == 1
        fulfilled = run_task_tool(
            "commitment.fulfill",
            {
                "commitment_id": commitment["commitment_id"],
                "resolution_note": "done in rehearsal",
            },
        )
        assert fulfilled and fulfilled["ok"] is True
        assert fulfilled["outputs"]["commitment"]["status"] == "fulfilled"
        listed_after = run_task_tool(
            "commitment.summary",
            {
                "task_name": "fourclaw-engage",
                "entity_id": "social-media-underling",
            },
        )
        assert listed_after["outputs"]["summary"]["fulfilled_count"] == 1


def test_choose_social_destination_skips_restricted_destination():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        with (
            patch(
                "hg_gateway.shared_storage.get_operational_state",
                return_value={"moltbook": {"announcements": {"error": "restricted - moderators only", "status_code": 403}}},
            ),
            patch(
                "hg_core.task_graph.native_task_tools._run",
                return_value=SimpleNamespace(
                    stdout=json.dumps(
                        {
                            "submolts": [
                                {"name": "announcements", "display_name": "Announcements"},
                                {"name": "general", "display_name": "General"},
                            ]
                        }
                    ),
                    returncode=0,
                ),
            ),
        ):
            choice = _choose_social_destination(
                workspace=root,
                platform="moltbook",
                content_hint="ship something loud",
                timeout_s=30,
            )
        assert choice["slug"] == "general"


def test_should_skip_reply_when_same_thread_was_hit_recently():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        with patch(
            "hg_gateway.shared_storage.get_operational_state",
            return_value={
                "rows": [
                    {
                        "platform": "fourclaw",
                        "thread_id": "thread-123",
                        "timestamp": "2026-06-10T10:00:00Z",
                    }
                ]
            },
        ):
            skip, reason = _should_skip_reply(
                root,
                platform="fourclaw",
                board="b",
                thread_id="thread-123",
                thread_context="Title: test\nOP: test",
                author="someone",
                reply_text="fresh insult",
            )
        assert skip is True
        assert reason == "repeat_target"


def test_signal_original_post_handoff_writes_platform_file():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        path = _signal_original_post_handoff(
            root,
            platform="fourclaw",
            source_task="fourclaw-engage",
            reason="engage_declined_noisy_thread",
            topic_hint="Title: Agent verification post",
            thread_id="thread-abc",
        )
        assert path is not None and path.is_file()
        loaded = _load_posting_handoff(root, "fourclaw")
        assert loaded is not None
        assert loaded.get("prefer_original_post") is True
        assert loaded.get("skipped_thread_id") == "thread-abc"


def test_consume_posting_handoff_marks_consumed():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        _signal_original_post_handoff(root, platform="moltbook", source_task="moltbook-engage", reason="test")
        _consume_posting_handoff(root, "moltbook")
        assert _load_posting_handoff(root, "moltbook") is None


def test_apply_posting_handoff_context_injects_guidance():
    handoff = {
        "guidance": "Post something fresh and original.",
        "topic_hint": "hot thread about verification",
    }
    goal, hint = _apply_posting_handoff_context(handoff, goal="autonomous post", content_hint="feed context")
    assert "fresh and original" in goal
    assert "Avoid revisiting" in hint


def test_engage_declined_no_action_signals_handoff_without_publish():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        with patch("hg_core.task_graph.native_task_tools._request_sleep_maintenance"):
            out = _engage_declined_no_action(
                root,
                task_name="fourclaw-engage",
                platform="fourclaw",
                decline_reason="this run stays quiet",
                thread_id="thread-abc",
                board="b",
                thread_context="Title: Agent verification post",
            )
        assert out["ok"] is True
        assert out["external_calls"] == 0
        result = out["outputs"]["result"]
        assert result["outcome_kind"] == "engage_declined"
        assert result["original_post_handoff"] is True
        assert _load_posting_handoff(root, "fourclaw") is not None


def test_should_hold_post_when_recent_topic_is_fatigued():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        automation_dir = root / "memory" / "automation" / "automation-underling-chan"
        automation_dir.mkdir(parents=True, exist_ok=True)
        (automation_dir / "posts.json").write_text(
            json.dumps(
                {
                    "posts": [
                        {"title": "Iran circus keeps getting worse", "timestamp": "2026-03-09T10:00:00Z"},
                        {"title": "Iran circus keeps getting worse again", "timestamp": "2026-03-09T09:00:00Z"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        hold, reason = _should_hold_post(
            root,
            platform="fourclaw",
            title="Iran circus keeps getting worse tonight",
            content="same angry geopolitical take",
        )
        assert hold is True
        assert reason == "repeat_topic"


def test_lifecycle_compose_candidates_defaults_to_open_choice_language():
    out = run_task_tool("lifecycle.compose_candidates", {"task_name": "fourclaw-auto-post", "platform": "fourclaw"})
    assert out is not None and out.get("ok") is True
    goal = out.get("outputs", {}).get("goal_for_execution", "")
    assert "take one good next step based on recent context" in goal


def test_ensure_social_context_files_bootstraps_defaults():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        _ensure_social_context_files(root)
        assert (root / "memory" / "automation" / "known_agents.json").exists()
        assert (root / "memory" / "automation" / "conversation_threads.json").exists()
        assert (root / "memory" / "automation" / "cross_platform_topics.json").exists()
        assert (root / "memory" / "automation" / "blocked_users.json").exists()
        assert not (root / "memory" / "research_queue.json").exists()
        summary = _social_context_summary(root)
        assert "Known entities:" in summary
        assert "research topics queued:" in summary


def test_persist_draft_artifact_writes_file():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        out = _persist_draft_artifact(
            workspace=root,
            task_name="fourclaw-engage",
            platform="fourclaw",
            mode="engage_draft",
            lifecycle={
                "memory_summary": "Recent posts: 4",
                "social_summary": "Known entities: 2",
                "knowledge_summary": "Knowledge context: test",
                "soul": "soul",
                "identity": "identity",
            },
            draft_text="draft text",
            goal="scheduled fourclaw engage run",
        )
        assert out
        p = Path(out)
        assert p.exists()
        payload = json.loads(p.read_text(encoding="utf-8"))
        assert payload["mode"] == "engage_draft"
        assert payload["draft_text"] == "draft text"


def test_lifecycle_tool_chain_writes_notification_and_sleep_request():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        with patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root):
            wake = run_task_tool("lifecycle.wakeup", {"task_name": "fourclaw-auto-post", "trigger": "cron"})
            assert wake is not None and wake.get("ok") is True
            assert wake.get("outputs", {}).get("result", {}).get("step") == "wakeup"

            contract = run_task_tool("lifecycle.get_runtime_contract", {"task_name": "fourclaw-auto-post", "platform": "fourclaw"})
            assert contract is not None and contract.get("ok") is True
            assert contract.get("outputs", {}).get("contract", {}).get("notify_tool") == "lifecycle.notify_human"
            assert contract.get("outputs", {}).get("contract", {}).get("agency_control_summary", {}).get("effective_mode") == "normal"
            assert contract.get("outputs", {}).get("contract", {}).get("knowledge_delivery_tool") == "knowledge.delivery_summary"
            assert contract.get("outputs", {}).get("contract", {}).get("knowledge_source_status_tool") == "knowledge.source_status"
            assert contract.get("outputs", {}).get("contract", {}).get("knowledge_feed_tool") is None
            assert contract.get("outputs", {}).get("contract", {}).get("confidence_summary_tool") == "confidence.summary"
            assert contract.get("outputs", {}).get("contract", {}).get("knowledge_search_tool") == "knowledge.search"
            assert contract.get("outputs", {}).get("contract", {}).get("knowledge_read_tool") == "knowledge.read"

            chooser = run_task_tool("lifecycle.choose_social_work", {"goal": "check replies and engage"})
            assert chooser is not None and chooser.get("ok") is True
            assert chooser.get("outputs", {}).get("mode") == "engage"

            ctx = run_task_tool("lifecycle.load_context", {"task_name": "fourclaw-auto-post", "platform": "fourclaw"})
            assert ctx is not None and ctx.get("ok") is True
            assert "memory_summary" in (ctx.get("outputs") or {})
            assert "confidence_summary" in (ctx.get("outputs") or {})

            read = run_task_tool(
                "lifecycle.read_content",
                {"task_name": "fourclaw-auto-post", "content_hint": "topic alpha", "limits": {"max_posts": 2, "max_comments": 4}},
            )
            assert read is not None and read.get("ok") is True
            assert read.get("outputs", {}).get("limits", {}).get("max_posts") == 2

            compose = run_task_tool(
                "lifecycle.compose_candidates",
                {"task_name": "fourclaw-auto-post", "platform": "fourclaw", "goal": "ship fast", "content_hint": "topic alpha"},
            )
            assert compose is not None and compose.get("ok") is True
            assert compose.get("outputs", {}).get("goal_for_execution")

            summarize = run_task_tool(
                "lifecycle.summarize_cycle",
                {
                    "task_name": "fourclaw-auto-post",
                    "execution_result": {"status": "completed", "thread_id": "x1"},
                    "read_result": {"status": "completed"},
                    "limits": {"max_posts": 1, "max_comments": 3},
                },
            )
            assert summarize is not None and summarize.get("ok") is True
            assert summarize.get("outputs", {}).get("summary", {}).get("execution", {}).get("status") == "completed"

            notify = run_task_tool(
                "lifecycle.prepare_notification",
                {"task_name": "fourclaw-auto-post", "summary": summarize.get("outputs", {}).get("summary", {})},
            )
            assert notify is not None and notify.get("ok") is True
            log_path = Path(notify.get("outputs", {}).get("notification_log", ""))
            assert log_path.exists()
            assert notify.get("outputs", {}).get("delivery", {}).get("attempted") is False
            assert notify.get("outputs", {}).get("notification_payload", {}).get("recipient") == "The Reverend"

            sleep = run_task_tool("lifecycle.request_sleep", {"task_name": "fourclaw-auto-post"})
            assert sleep is not None and sleep.get("ok") is True
            sleep_path = Path(sleep.get("outputs", {}).get("sleep_request", ""))
            assert sleep_path.exists()
            cadence_path = Path(sleep.get("outputs", {}).get("cadence_request", ""))
            assert cadence_path.exists()
            assert (root / "memory" / "automation" / "automation-fourclaw-auto-post" / "sleep_request.json").exists()
            assert (root / "memory" / "automation" / "automation-underling-chan" / "cadence_request.json").exists()
            assert sleep.get("outputs", {}).get("request", {}).get("reason") == "dag_engage_cycle_complete"


def test_runtime_contract_includes_held_agency_control():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        operational_dir = root / "memory" / "automation" / "automation-underling-chan"
        operational_dir.mkdir(parents=True, exist_ok=True)
        (operational_dir / "agency_control.json").write_text(
            json.dumps({"mode": "held", "reason": "maintenance window", "updated_by": "operator"}),
            encoding="utf-8",
        )
        with patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root):
            contract = run_task_tool("lifecycle.get_runtime_contract", {"task_name": "fourclaw-auto-post", "platform": "fourclaw"})
        assert contract is not None and contract.get("ok") is True
        summary = contract.get("outputs", {}).get("contract", {}).get("agency_control_summary", {})
        assert summary.get("effective_mode") == "held"
        assert summary.get("reason") == "maintenance window"


def test_run_task_tool_blocks_when_agency_control_held():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        operational_dir = root / "memory" / "automation" / "automation-underling-chan"
        operational_dir.mkdir(parents=True, exist_ok=True)
        (operational_dir / "agency_control.json").write_text(
            json.dumps({"mode": "held", "reason": "manual freeze", "updated_by": "operator"}),
            encoding="utf-8",
        )
        with patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root):
            blocked = run_task_tool("fourclaw-auto-post", {"goal": "post something"}, timeout_s=30)
        assert blocked is not None
        assert blocked.get("ok") is False
        assert blocked.get("error") == "agency_control_held"
        assert blocked.get("outputs", {}).get("result", {}).get("status") == "blocked"
        assert blocked.get("outputs", {}).get("agency_control_summary", {}).get("effective_mode") == "held"
        log_path = Path(blocked.get("outputs", {}).get("notification_log", ""))
        assert log_path.exists()
        lines = log_path.read_text(encoding="utf-8").splitlines()
        assert any("agency_control_held" in line for line in lines)


def test_run_task_tool_blocks_outbound_lane_when_agency_control_review_only():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        operational_dir = root / "memory" / "automation" / "automation-underling-chan"
        operational_dir.mkdir(parents=True, exist_ok=True)
        (operational_dir / "agency_control.json").write_text(
            json.dumps({"mode": "review_only", "reason": "supervised lane", "updated_by": "operator"}),
            encoding="utf-8",
        )
        gateway_db = root / "memory" / "gateway.sqlite3"
        from hg_gateway.approval_service import ApprovalService

        with (
            patch.dict(os.environ, {"HG_GATEWAY_DB_PATH": str(gateway_db)}, clear=False),
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
        ):
            blocked = run_task_tool("fourclaw-auto-post", {"goal": "post something"}, timeout_s=30)
        assert blocked is not None
        assert blocked.get("ok") is False
        assert blocked.get("error") == "agency_control_review_only"
        assert blocked.get("outputs", {}).get("result", {}).get("step") == "agency_control_review"
        assert blocked.get("outputs", {}).get("result", {}).get("status") == "pending_approval"
        assert blocked.get("outputs", {}).get("approval_id")
        draft_artifact = Path(blocked.get("outputs", {}).get("draft_artifact", ""))
        assert draft_artifact.exists()
        assert blocked.get("outputs", {}).get("agency_control_summary", {}).get("effective_mode") == "review_only"
        pending = ApprovalService(db_path=str(gateway_db)).list_pending()
        assert len(pending) == 1
        assert pending[0]["entity_id"] == "fourclaw-auto-post"
        assert pending[0]["action_kind"] == "social_write"
        log_path = Path(blocked.get("outputs", {}).get("notification_log", ""))
        assert log_path.exists()
        lines = log_path.read_text(encoding="utf-8").splitlines()
        assert any("agency_control_review_only" in line for line in lines)
        latest = json.loads(lines[-1])
        assert latest["summary"]["execution"]["status"] == "pending_approval"
        assert latest["summary"]["review_handoff"]["approval_id"] == blocked.get("outputs", {}).get("approval_id")


def test_run_task_tool_blocks_auto_post_when_outbound_lane_policy_replies_only():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        operational_dir = root / "memory" / "automation" / "automation-underling-chan"
        operational_dir.mkdir(parents=True, exist_ok=True)
        (operational_dir / "agency_control.json").write_text(
            json.dumps({"mode": "normal", "reason": "reply windows only", "updated_by": "operator", "outbound_lane_policy": "replies_only"}),
            encoding="utf-8",
        )
        with patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root):
            blocked = run_task_tool("fourclaw-auto-post", {"goal": "post something"}, timeout_s=30)
        assert blocked is not None
        assert blocked.get("ok") is False
        assert blocked.get("error") == "agency_lane_policy_blocked"
        assert blocked.get("outputs", {}).get("result", {}).get("step") == "agency_lane_policy_block"
        assert blocked.get("outputs", {}).get("agency_control_summary", {}).get("outbound_lane_policy") == "replies_only"
        assert blocked.get("outputs", {}).get("agency_control_summary", {}).get("allowed_outbound_modes") == ["engage"]


def test_run_task_tool_allows_engage_when_outbound_lane_policy_replies_only():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        operational_dir = root / "memory" / "automation" / "automation-underling-chan"
        operational_dir.mkdir(parents=True, exist_ok=True)
        (operational_dir / "agency_control.json").write_text(
            json.dumps({"mode": "normal", "reason": "reply windows only", "updated_by": "operator", "outbound_lane_policy": "replies_only"}),
            encoding="utf-8",
        )
        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch("hg_core.task_graph.native_task_tools._task_tool_engage", return_value={"ok": True, "outputs": {"result": {"status": "completed"}}, "returncode": 0, "external_calls": 0}),
        ):
            out = run_task_tool("fourclaw-engage", {"goal": "check replies"}, timeout_s=30)
        assert out is not None
        assert out.get("ok") is True


def test_run_task_tool_blocks_outbound_lane_when_outbound_budget_exhausted():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        operational_dir = root / "memory" / "automation" / "automation-underling-chan"
        operational_dir.mkdir(parents=True, exist_ok=True)
        (operational_dir / "agency_control.json").write_text(
            json.dumps(
                {
                    "mode": "normal",
                    "reason": "daily cap reached",
                    "updated_by": "operator",
                    "daily_outbound_budget": 1,
                    "outbound_actions_window_hours": 24,
                }
            ),
            encoding="utf-8",
        )
        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch("hg_core.task_graph.native_task_tools._live_social_enabled", return_value=True),
            patch(
                "hg_core.task_graph.native_task_tools._agency_control_summary_for_task",
                return_value={
                    "status": "normal",
                    "mode": "normal",
                    "effective_mode": "normal",
                    "reason": "daily cap reached",
                    "daily_outbound_budget": 1,
                    "recent_outbound_action_count": 1,
                    "outbound_actions_window_hours": 24,
                    "outbound_budget_remaining": 0,
                    "outbound_budget_exhausted": True,
                    "outbound_lane_policy": "unrestricted",
                    "allowed_outbound_modes": ["engage"],
                },
            ),
        ):
            blocked = run_task_tool("fourclaw-auto-post", {"goal": "post something"}, timeout_s=30)
        assert blocked is not None
        assert blocked.get("ok") is False
        assert blocked.get("error") == "agency_outbound_budget_exhausted"
        assert blocked.get("outputs", {}).get("result", {}).get("step") == "agency_outbound_budget"
        assert blocked.get("outputs", {}).get("agency_control_summary", {}).get("daily_outbound_budget") == 1
        assert blocked.get("outputs", {}).get("agency_control_summary", {}).get("recent_outbound_action_count") == 1
        assert blocked.get("outputs", {}).get("agency_control_summary", {}).get("outbound_budget_exhausted") is True


def test_run_task_tool_allows_outbound_lane_when_budget_remaining():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        operational_dir = root / "memory" / "automation" / "automation-underling-chan"
        operational_dir.mkdir(parents=True, exist_ok=True)
        (operational_dir / "agency_control.json").write_text(
            json.dumps(
                {
                    "mode": "normal",
                    "reason": "cap outbound churn",
                    "updated_by": "operator",
                    "daily_outbound_budget": 3,
                    "outbound_actions_window_hours": 24,
                }
            ),
            encoding="utf-8",
        )
        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch("operator_console.server.app.services.operational_agency_control._recent_outbound_action_count", return_value=1),
            patch("hg_core.task_graph.native_task_tools._task_tool_auto_post", return_value={"ok": True, "outputs": {"result": {"status": "completed"}}, "returncode": 0, "external_calls": 0}),
        ):
            out = run_task_tool("fourclaw-auto-post", {"goal": "post something"}, timeout_s=30)
        assert out is not None
        assert out.get("ok") is True


def test_knowledge_search_tool_returns_results(monkeypatch):
    with patch(
        "operator_console.server.app.services.knowledge_service.search",
        return_value=[
            {
                "file_path": "technology/ai-state.md",
                "title": "AI State",
                "category": "technology",
                "snippet": "Recent model updates.",
            }
        ],
    ):
        out = run_task_tool("knowledge.search", {"query": "AI state", "limit": 3})
    assert out is not None and out.get("ok") is True
    assert out.get("outputs", {}).get("result", {}).get("step") == "knowledge_search"
    assert out.get("outputs", {}).get("results", [])[0]["title"] == "AI State"


def test_knowledge_read_tool_returns_document(monkeypatch):
    with patch(
        "operator_console.server.app.services.knowledge_service.read_document",
        return_value={
            "file_path": "technology/ai-state.md",
            "title": "AI State",
            "category": "technology",
            "content": "Recent model updates and deployment notes.",
            "content_truncated": False,
        },
    ):
        out = run_task_tool("knowledge.read", {"file_path": "technology/ai-state.md", "max_chars": 2000})
    assert out is not None and out.get("ok") is True
    assert out.get("outputs", {}).get("result", {}).get("step") == "knowledge_read"
    assert out.get("outputs", {}).get("document", {}).get("title") == "AI State"


def test_knowledge_read_tool_reports_not_found(monkeypatch):
    with patch(
        "operator_console.server.app.services.knowledge_service.read_document",
        return_value=None,
    ):
        out = run_task_tool("knowledge.read", {"title": "Missing Doc"})
    assert out is not None and out.get("ok") is False
    assert out.get("error") == "knowledge_document_not_found"


def test_knowledge_delivery_summary_tool_returns_recent_delivery_data(monkeypatch):
    summary = {
        "history_path": "db:knowledge:research_history:knowledge-research-auto-v2",
        "recent_topics": [{"topic": "AI infrastructure", "file_path": "knowledge/technology/ai-infrastructure.md"}],
        "recent_topic_count": 1,
        "latest_brief_path": "knowledge/current_events/brief-2026-03-13.md",
        "latest_brief_preview": "# Current Events Brief",
        "latest_brief_truncated": False,
        "queue": [{"topic": "Health"}],
    }
    with patch(
        "operator_console.server.app.services.knowledge_service.get_delivery_summary",
        return_value=summary,
    ):
        out = run_task_tool("knowledge.delivery_summary", {"limit": 3, "max_chars": 2000})
    assert out is not None and out.get("ok") is True
    assert out.get("outputs", {}).get("result", {}).get("step") == "knowledge_delivery_summary"
    assert out.get("outputs", {}).get("summary", {}).get("latest_brief_path") == "knowledge/current_events/brief-2026-03-13.md"


def test_knowledge_source_status_tool_returns_effective_source_state(monkeypatch):
    source_state = {
        "sources": {
            "brave": {"enabled": True, "news_count": 4, "web_count": 5},
            "google_news": {"enabled": True, "news_count": 2, "hl": "en-US", "gl": "US", "ceid": "US:en"},
            "local_news": {"enabled": False, "url_count": 0, "urls": [], "timeout_s": 8},
        }
    }
    with patch(
        "operator_console.server.app.services.knowledge_service.get_source_config_state",
        return_value=source_state,
    ):
        out = run_task_tool("knowledge.source_status", {})
    assert out is not None and out.get("ok") is True
    assert out.get("outputs", {}).get("result", {}).get("step") == "knowledge_source_status"
    assert out.get("outputs", {}).get("result", {}).get("enabled_sources") == ["brave", "google_news"]
    assert out.get("outputs", {}).get("sources", {}).get("google_news", {}).get("enabled") is True


def test_knowledge_runtime_contract_includes_feed_tool():
    contract = run_task_tool("lifecycle.get_runtime_contract", {"task_name": "knowledge-research-auto-v2", "platform": "knowledge"})
    assert contract is not None and contract.get("ok") is True
    assert contract.get("outputs", {}).get("contract", {}).get("knowledge_feed_tool") == "lifecycle.read_knowledge_feed"
    assert contract.get("outputs", {}).get("contract", {}).get("knowledge_source_status_tool") == "knowledge.source_status"
    assert contract.get("outputs", {}).get("contract", {}).get("confidence_summary_tool") == "confidence.summary"


def test_lifecycle_read_knowledge_feed_returns_delivery_summary():
    summary = {
        "history_path": "db:knowledge:research_history:knowledge-research-auto-v2",
        "recent_topics": [{"topic": "AI infrastructure"}],
        "recent_topic_count": 1,
        "latest_brief_path": "knowledge/current_events/brief-2026-03-13.md",
        "latest_brief_preview": "# Current Events Brief",
        "latest_brief_truncated": False,
        "queue": [{"topic": "Health"}],
    }
    source_state = {
        "sources": {
            "brave": {"enabled": True, "news_count": 4, "web_count": 5},
            "google_news": {"enabled": True, "news_count": 2, "hl": "en-US", "gl": "US", "ceid": "US:en"},
            "local_news": {"enabled": False, "url_count": 0, "urls": [], "timeout_s": 8},
        }
    }
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch("operator_console.server.app.services.knowledge_service.get_delivery_summary", return_value=summary),
            patch("operator_console.server.app.services.knowledge_service.get_source_config_state", return_value=source_state),
        ):
            out = run_task_tool("lifecycle.read_knowledge_feed", {"task_name": "knowledge-research-auto-v2"})
    assert out is not None and out.get("ok") is True
    assert out.get("outputs", {}).get("result", {}).get("step") == "read_knowledge_feed"
    assert out.get("outputs", {}).get("delivery_summary", {}).get("latest_brief_path") == "knowledge/current_events/brief-2026-03-13.md"
    assert out.get("outputs", {}).get("source_status", {}).get("sources", {}).get("google_news", {}).get("enabled") is True


def test_load_context_uses_richer_knowledge_wake_briefing_for_research_task():
    summary = {
        "history_path": "db:knowledge:research_history:knowledge-research-auto-v2",
        "recent_topics": [{"topic": "AI infrastructure"}, {"topic": "GPU supply"}],
        "recent_topic_count": 2,
        "latest_brief_path": "knowledge/current_events/brief-2026-03-13.md",
        "latest_brief_preview": "# Current Events Brief",
        "latest_brief_truncated": False,
        "queue": [{"topic": "Health"}],
    }
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch("operator_console.server.app.services.knowledge_service.get_delivery_summary", return_value=summary),
            patch(
                "operator_console.server.app.services.knowledge_service.get_source_config_state",
                return_value={
                    "sources": {
                        "brave": {"enabled": True, "news_count": 4, "web_count": 5},
                        "google_news": {"enabled": True, "news_count": 2, "hl": "en-US", "gl": "US", "ceid": "US:en"},
                        "local_news": {"enabled": False, "url_count": 0, "urls": [], "timeout_s": 8},
                    }
                },
            ),
        ):
            out = run_task_tool("lifecycle.load_context", {"task_name": "knowledge-research-auto-v2", "platform": "knowledge"})
    assert out is not None and out.get("ok") is True
    knowledge_summary = out.get("outputs", {}).get("knowledge_summary", "")
    assert "Research delivered: AI infrastructure, GPU supply" in knowledge_summary
    assert "Research sources active: Brave news/web (4/5), Google News RSS (2; en-US/US)" in knowledge_summary
    assert "Queued next: Health" in knowledge_summary
    assert "Latest brief: knowledge/current_events/brief-2026-03-13.md" in knowledge_summary


def test_load_context_gives_non_knowledge_task_research_delivery_summary():
    summary = {
        "history_path": "db:knowledge:research_history:knowledge-research-auto-v2",
        "recent_topics": [{"topic": "AI infrastructure"}, {"topic": "Moltbook moderation"}],
        "recent_topic_count": 2,
        "latest_brief_path": "knowledge/current_events/brief-2026-03-13.md",
        "latest_brief_preview": "# Current Events Brief",
        "latest_brief_truncated": False,
        "queue": [],
    }
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch("operator_console.server.app.services.knowledge_service.get_delivery_summary", return_value=summary),
            patch(
                "operator_console.server.app.services.knowledge_service.get_source_config_state",
                return_value={
                    "sources": {
                        "brave": {"enabled": True, "news_count": 6, "web_count": 3},
                        "google_news": {"enabled": False, "news_count": 4, "hl": "en-US", "gl": "US", "ceid": "US:en"},
                        "local_news": {"enabled": True, "url_count": 1, "urls": ["https://local.test/rss.xml"], "timeout_s": 5},
                    }
                },
            ),
        ):
            out = run_task_tool("lifecycle.load_context", {"task_name": "fourclaw-auto-post", "platform": "fourclaw"})
    assert out is not None and out.get("ok") is True
    knowledge_summary = out.get("outputs", {}).get("knowledge_summary", "")
    assert "Research sources active: Brave news/web (6/3), Local feeds (1)" in knowledge_summary
    assert "Topics you can request (examples): AI infrastructure, Moltbook moderation" in knowledge_summary
    assert "Current-events brief: knowledge/current_events/brief-2026-03-13.md" in knowledge_summary


def test_load_context_prefers_actual_research_deliveries_for_entity():
    summary = {
        "history_path": "db:knowledge:research_history:knowledge-research-auto-v2",
        "recent_topics": [{"topic": "AI infrastructure"}, {"topic": "Moltbook moderation"}],
        "recent_topic_count": 2,
        "latest_brief_path": "knowledge/current_events/brief-2026-03-13.md",
        "latest_brief_preview": "# Current Events Brief",
        "latest_brief_truncated": False,
        "queue": [],
    }
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        save_operational_json_state(
            root,
            state_key="research_deliveries",
            payload={
                "deliveries": [
                    {"requested_by": "automation-fourclaw-auto-post", "topic": "Bayman continuity", "file_path": "knowledge/technology/bayman-continuity.md"},
                    {"requested_by": "someone-else", "topic": "Ignore me", "file_path": "knowledge/general/ignore-me.md"},
                ]
            },
        )
        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch("operator_console.server.app.services.knowledge_service.get_delivery_summary", return_value=summary),
            patch(
                "operator_console.server.app.services.knowledge_service.get_source_config_state",
                return_value={
                    "sources": {
                        "brave": {"enabled": True, "news_count": 4, "web_count": 5},
                        "google_news": {"enabled": False, "news_count": 4, "hl": "en-US", "gl": "US", "ceid": "US:en"},
                        "local_news": {"enabled": False, "url_count": 0, "urls": [], "timeout_s": 8},
                    }
                },
            ),
        ):
            out = run_task_tool("lifecycle.load_context", {"task_name": "fourclaw-auto-post", "platform": "fourclaw"})
    assert out is not None and out.get("ok") is True
    knowledge_summary = out.get("outputs", {}).get("knowledge_summary", "")
    assert "Research delivered for you: Bayman continuity" in knowledge_summary
    assert "Research sources active: Brave news/web (4/5)" in knowledge_summary
    assert "Topics you can request (examples): AI infrastructure, Moltbook moderation" in knowledge_summary


def test_thread_url_for_platform_agentchan_aichan():
    assert _thread_url_for_platform("agentchan", "2309", board="b") == "https://agentchan.org/b/thread/2309"
    assert _thread_url_for_platform("aichan", "660", board="biz") == "https://aichan.lol/biz/res/660.html"
    assert _thread_url_for_platform("agentchan", "1") == "https://agentchan.org/b/thread/1"
    assert _thread_url_for_platform("aichan", "2") == "https://aichan.lol/b/res/2.html"
    assert _thread_url_for_platform("fourclaw", "abc") == "https://www.4claw.org/t/abc"
    assert _thread_url_for_platform("moltbook", "xyz") == "https://www.moltbook.com/post/xyz"


def test_format_lifecycle_notification_snippet_knowledge_note():
    entry = {
        "timestamp": "2026-03-11T17:00:00Z",
        "task_name": "aichan-auto-post",
        "channel": "human",
        "summary": {
            "execution": {
                "status": "completed",
                "thread_id": "660",
                "board": "biz",
                "title_snippet": "A short title",
                "body_snippet": "First part of the post body here.",
            },
            "knowledge_summary": "2 items saved: topic A, topic B.",
        },
    }
    msg = _format_lifecycle_notification(entry)
    assert "- snippet:" in msg and "A short title" in msg and "First part of the post body" in msg
    assert "- knowledge:" in msg and "2 items saved" in msg
    entry2 = {
        "timestamp": "2026-03-11T17:00:00Z",
        "task_name": "fourclaw-engage",
        "channel": "human",
        "summary": {"execution": {"status": "no_action", "note": "Held action for repeatauthorloop."}},
    }
    msg2 = _format_lifecycle_notification(entry2)
    assert "no_action" in msg2 and "note:" in msg2 and "repeatauthorloop" in msg2


def test_format_lifecycle_notification_never_raises():
    """_format_lifecycle_notification never raises; returns minimal lifecycle string for malformed entry."""
    msg = _format_lifecycle_notification({})
    assert "Lifecycle" in msg
    assert "- task:" in msg
    assert "- status:" in msg
    assert "- timestamp:" in msg
    msg2 = _format_lifecycle_notification({"summary": "not a dict"})
    assert "Lifecycle" in msg2 and "- task:" in msg2
    msg3 = _format_lifecycle_notification({"task_name": "my-job", "timestamp": "2026-01-01T00:00:00Z", "summary": None})
    assert "Lifecycle" in msg3 and "my-job" in msg3
    msg4 = _format_lifecycle_notification({"task_name": "failed-job", "summary": {"execution": {"status": "failed"}}})
    assert "Lifecycle" in msg4 and "failed" in msg4


def test_lifecycle_notification_delivery_via_ingest_no_send():
    """DAG run-complete notifications are not sent here; delivery is via ingest only."""
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch.dict(os.environ, {"HG_ENABLE_LIFECYCLE_TELEGRAM": "1"}),
            patch("hg_core.notification_telegram.send_telegram", return_value={"ok": True}) as mock_send,
        ):
            notify = run_task_tool(
                "lifecycle.prepare_notification",
                {"task_name": "fourclaw-auto-post", "summary": {"execution": {"status": "completed"}}},
            )
            assert notify is not None and notify.get("ok") is True
            delivery = notify.get("outputs", {}).get("delivery", {})
            assert delivery.get("skipped") == "delivery_via_ingest"
            assert delivery.get("sent") is False
            assert delivery.get("recipient") == "The Reverend"
            assert delivery.get("channel") == "human"
            mock_send.assert_not_called()
            payload = notify.get("outputs", {}).get("notification_payload", {})
            assert payload.get("task_name") == "fourclaw-auto-post"
            assert payload.get("transport") == "configured_channel"


def test_lifecycle_notification_skipped_when_explicitly_disabled():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch.dict(os.environ, {"HG_ENABLE_LIFECYCLE_TELEGRAM": "0"}),
        ):
            notify = run_task_tool(
                "lifecycle.prepare_notification",
                {"task_name": "fourclaw-auto-post", "summary": {"execution": {"status": "completed"}}},
            )
            assert notify is not None and notify.get("ok") is True
            assert notify.get("outputs", {}).get("delivery", {}).get("skipped") == "delivery_via_ingest"
            assert notify.get("outputs", {}).get("delivery", {}).get("attempted") is False
            assert notify.get("outputs", {}).get("delivery", {}).get("transport") == "log_only"


def test_lifecycle_notify_human_alias_matches_prepare_notification():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        with patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root):
            notify = run_task_tool(
                "lifecycle.notify_human",
                {
                    "task_name": "fourclaw-auto-post",
                    "kind": "help_request",
                    "message": "Need help with rate-limit investigation.",
                    "summary": {"execution": {"status": "needs_help"}},
                },
            )
            assert notify is not None and notify.get("ok") is True
            payload = notify.get("outputs", {}).get("notification_payload", {})
            assert payload.get("recipient") == "The Reverend"
            assert payload.get("kind") == "help_request"
            assert "rate-limit investigation" in payload.get("message", "")


def test_lifecycle_request_sleep_captures_duration_and_defer_metadata():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        with patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root):
            sleep = run_task_tool(
                "lifecycle.request_sleep",
                {
                    "task_name": "moltbook-engage",
                    "reason": "wait_for_reply_window",
                    "duration_minutes": 45,
                    "minimum_sleep_minutes": 15,
                    "scheduler_job_id": "social-media-underling",
                },
            )
            assert sleep is not None and sleep.get("ok") is True
            payload = sleep.get("outputs", {}).get("request", {})
            assert payload.get("reason") == "wait_for_reply_window"
            assert payload.get("requested_duration_minutes") == 45
            assert payload.get("minimum_sleep_minutes") == 15
            assert payload.get("not_before")
            cadence = sleep.get("outputs", {}).get("cadence", {})
            assert cadence.get("requested_duration_minutes") == 45
            assert cadence.get("minimum_sleep_minutes") == 15
            assert cadence.get("job_id") == "social-media-underling"


def test_lifecycle_choose_social_work_prefers_stale_candidate(tmp_path):
    run_log = tmp_path / "memory" / "automation" / "run_summaries.jsonl"
    run_log.parent.mkdir(parents=True, exist_ok=True)
    now_ms = int(datetime(2026, 3, 13, tzinfo=timezone.utc).timestamp() * 1000)
    rows = [
        {"job_id": "moltbook-engage", "session_target": "automation-moltbook", "summary": "x", "ts_ms": now_ms},
        {"job_id": "fourclaw-engage", "session_target": "automation-fourclaw", "summary": "x", "ts_ms": now_ms - 10000},
        {"job_id": "agentchan-engage", "session_target": "automation-agentchan", "summary": "x", "ts_ms": now_ms - 20000},
    ]
    run_log.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    with patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=tmp_path):
        out = run_task_tool("lifecycle.choose_social_work", {"goal": "check replies and engage"})
    assert out is not None and out.get("ok") is True
    assert out.get("outputs", {}).get("task_name") == "aichan-engage" or out.get("outputs", {}).get("task_name") == "agentchan-engage"
    assert out.get("outputs", {}).get("mode") == "engage"


def test_lifecycle_choose_social_work_scopes_to_operational_identity():
    out = run_task_tool(
        "lifecycle.choose_social_work",
        {"task_name": "fourclaw-engage", "goal": "check replies and engage"},
    )
    assert out is not None and out.get("ok") is True
    candidates = out.get("outputs", {}).get("candidates", [])
    platforms = {row.get("platform") for row in candidates if isinstance(row, dict)}
    assert "moltbook" not in platforms
    assert {"fourclaw", "aichan"}.issubset(platforms)
    assert out.get("outputs", {}).get("operational_agent_id") == "underling-chan"


def test_lifecycle_choose_social_work_scopes_bayman_to_bayman_tasks():
    out = run_task_tool(
        "lifecycle.choose_social_work",
        {"task_name": "newfoundland-bayman-fourclaw-engage", "goal": "check replies and engage"},
    )
    assert out is not None and out.get("ok") is True
    candidates = out.get("outputs", {}).get("candidates", [])
    task_names = {row.get("task_name") for row in candidates if isinstance(row, dict)}
    assert "newfoundland-bayman-fourclaw-engage" in task_names
    assert "fourclaw-engage" not in task_names
    assert out.get("outputs", {}).get("operational_agent_id") == "newfoundland-bayman"


def test_lifecycle_choose_social_work_skips_recently_denied_agentchan(tmp_path):
    run_log = tmp_path / "memory" / "automation" / "run_summaries.jsonl"
    run_log.parent.mkdir(parents=True, exist_ok=True)
    now_ms = int(datetime(2026, 3, 13, tzinfo=timezone.utc).timestamp() * 1000)
    rows = [
        {"job_id": "agentchan-auto-post", "session_target": "automation-underling-chan", "summary": "x", "ts_ms": now_ms - 50000},
        {"job_id": "aichan-engage", "session_target": "automation-underling-chan", "summary": "x", "ts_ms": now_ms - 10000},
    ]
    run_log.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    agentchan_log = tmp_path / "agentchan" / "api_async.log"
    agentchan_log.parent.mkdir(parents=True, exist_ok=True)
    agentchan_log.write_text(
        '{"error":{"code":"BOARD_ACCESS_DENIED","message":"You do not have access to /ai/"}}' + "\n",
        encoding="utf-8",
    )
    with patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=tmp_path):
        out = run_task_tool("lifecycle.choose_social_work", {"task_name": "fourclaw-engage", "goal": "write a post"})
    assert out is not None and out.get("ok") is True
    candidates = out.get("outputs", {}).get("candidates", [])
    assert all(row.get("platform") != "agentchan" for row in candidates if isinstance(row, dict))


def test_lifecycle_dispatch_social_work_executes_selected_task():
    original_run_task_tool = run_task_tool

    def _fake_run_task_tool(name, inputs, timeout_s=300):
        if name == "moltbook-engage":
            return {"ok": True, "outputs": {"result": {"status": "completed", "task_name": "moltbook-engage"}}, "returncode": 0, "external_calls": 0}
        return original_run_task_tool(name, inputs, timeout_s=timeout_s)

    with patch(
        "hg_core.task_graph.native_task_tools.run_task_tool",
        side_effect=_fake_run_task_tool,
    ):
        out = _task_tool_lifecycle_dispatch_social_work(
            "lifecycle.dispatch_social_work",
            {"task_name": "moltbook-engage", "goal": "check replies"},
        )
    assert out.get("ok") is True
    assert out.get("outputs", {}).get("task_name") == "moltbook-engage"


def test_lifecycle_notification_includes_approval_id_in_formatted_payload():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch.dict(os.environ, {"HG_ENABLE_LIFECYCLE_TELEGRAM": "1"}),
            patch("hg_core.notification_telegram.send_telegram", return_value={"ok": True}) as mock_send,
        ):
            notify = run_task_tool(
                "lifecycle.prepare_notification",
                {
                    "task_name": "fourclaw-auto-post",
                    "summary": {"execution": {"status": "awaiting_approval", "approval_id": "apr-123"}},
                },
            )
            mock_send.assert_not_called()
            payload = notify.get("outputs", {}).get("notification_payload", {})
            msg = _format_lifecycle_notification(payload)
            assert "approval_id" in msg and "approve in console" in msg


def test_lifecycle_notification_payload_uses_post_url_when_present():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch.dict(os.environ, {"HG_ENABLE_LIFECYCLE_TELEGRAM": "1"}),
            patch("hg_core.notification_telegram.send_telegram", return_value={"ok": True}) as mock_send,
        ):
            notify = run_task_tool(
                "lifecycle.prepare_notification",
                {
                    "task_name": "moltbook-auto-post",
                    "summary": {
                        "execution": {
                            "status": "completed",
                            "platform": "moltbook",
                            "post_url": "https://www.moltbook.com/post/abc123",
                        }
                    },
                },
            )
            mock_send.assert_not_called()
            payload = notify.get("outputs", {}).get("notification_payload", {})
            msg = _format_lifecycle_notification(payload)
            assert "https://www.moltbook.com/post/abc123" in msg


def test_lifecycle_notification_includes_note_when_no_verified_link():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch.dict(os.environ, {"HG_ENABLE_LIFECYCLE_TELEGRAM": "1"}),
            patch("hg_core.notification_telegram.send_telegram", return_value={"ok": True}) as mock_send,
        ):
            notify = run_task_tool(
                "lifecycle.prepare_notification",
                {
                    "task_name": "moltbook-engage",
                    "summary": {
                        "execution": {
                            "status": "no_action",
                            "platform": "moltbook",
                            "note": "No verified Moltbook reply link was produced for this cycle.",
                        }
                    },
                },
            )
            mock_send.assert_not_called()
            payload = notify.get("outputs", {}).get("notification_payload", {})
            msg = _format_lifecycle_notification(payload)
            assert "status: `no_action`" in msg
            assert "No verified Moltbook reply link was produced for this cycle." in msg


def test_lifecycle_read_content_uses_live_thread_context_when_available():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch("hg_core.task_graph.native_task_tools._pick_thread_id", return_value="t-123"),
            patch(
                "hg_core.task_graph.native_task_tools._fetch_thread_payload",
                return_value={"data": {"thread": {"title": "Signal chain", "content": "Read this first"}, "posts": []}},
            ),
        ):
            read = run_task_tool(
                "lifecycle.read_content",
                {"task_name": "fourclaw-auto-post", "limits": {"max_posts": 2, "max_comments": 4}},
            )
            assert read is not None and read.get("ok") is True
            outputs = read.get("outputs", {})
            assert outputs.get("live_read") is True
            assert outputs.get("read_details", {}).get("thread_id") == "t-123"
            assert "Signal chain" in str(outputs.get("content_hint", ""))
            assert int(read.get("external_calls") or 0) >= 2


def test_engage_execute_task_receives_content_hint_and_goal_for_execution():
    """run_task_tool for engage resolves content_hint and goal_for_execution and passes them to _task_tool_engage."""
    engage_out = {
        "ok": True,
        "outputs": {"result": {"status": "completed", "mode": "text_only"}, "reply_text": "ok"},
        "returncode": 0,
        "external_calls": 0,
    }
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch("hg_core.task_graph.native_task_tools._task_tool_engage", return_value=engage_out) as mock_engage,
        ):
            out = run_task_tool(
                "fourclaw-engage",
                {
                    "goal": "raw goal",
                    "content_hint": "Recent feed: thread about X",
                    "goal_for_execution": "Composed goal from draft_candidates",
                },
                timeout_s=30,
            )
    assert out is not None and out.get("ok") is True
    mock_engage.assert_called_once()
    call_kwargs = mock_engage.call_args[1]
    assert call_kwargs.get("content_hint") == "Recent feed: thread about X"
    assert call_kwargs.get("goal_for_execution") == "Composed goal from draft_candidates"
    assert call_kwargs.get("goal") == "raw goal"


def test_engage_execute_task_unresolved_refs_coerced_to_empty():
    """Unresolved $node.* refs for content_hint and goal_for_execution are coerced to empty string; no crash."""
    engage_out = {
        "ok": True,
        "outputs": {"result": {"status": "completed", "mode": "text_only"}, "reply_text": "ok"},
        "returncode": 0,
        "external_calls": 0,
    }
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch("hg_core.task_graph.native_task_tools._task_tool_engage", return_value=engage_out) as mock_engage,
        ):
            out = run_task_tool(
                "fourclaw-engage",
                {
                    "goal": "fallback goal",
                    "content_hint": "$node.read_content_queue.content_hint",
                    "goal_for_execution": "$node.draft_candidates.goal_for_execution",
                },
                timeout_s=30,
            )
    assert out is not None and out.get("ok") is True
    mock_engage.assert_called_once()
    call_kwargs = mock_engage.call_args[1]
    assert call_kwargs.get("content_hint") == ""
    assert call_kwargs.get("goal_for_execution") == ""
    assert call_kwargs.get("goal") == "fallback goal"


def test_auto_post_requires_human_approval_before_live_write(monkeypatch):
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        db_path = root / "gateway.sqlite3"
        monkeypatch.setenv("HG_DB_PATH", str(db_path))
        monkeypatch.setenv("HG_ENABLE_LIVE_SOCIAL_APIS", "1")
        monkeypatch.setenv("HG_FORCE_SOCIAL_WRITE_APPROVAL", "1")
        with patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root):
            out = run_task_tool("fourclaw-auto-post", {"goal": "post about agent governance"}, timeout_s=30)
        assert out is not None and out.get("ok") is True
        outputs = out.get("outputs", {})
        assert outputs.get("approval_id")
        assert outputs.get("result", {}).get("status") == "pending_approval"
        assert Path(outputs.get("draft_artifact", "")).exists()


def test_auto_post_policy_can_auto_approve_social_write(monkeypatch):
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        db_path = root / "gateway.sqlite3"
        monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
        monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
        monkeypatch.setenv("HG_ENABLE_LIVE_SOCIAL_APIS", "1")
        monkeypatch.setenv("HG_OPERATOR_TENANT_ID", "default")
        from hg_gateway import store as store_module
        store_module._store = None
        from hg_gateway.store import get_store

        get_store().tenant_settings_upsert(
            "default",
            approval_rules=[
                {
                    "id": "rule-fourclaw-posts",
                    "label": "Auto approve Fourclaw auto posts",
                    "kinds": ["social_write"],
                    "risks": ["high"],
                    "workflow_ids": ["fourclaw-auto-post"],
                    "platforms": ["fourclaw"],
                    "modes": ["post"],
                    "enabled": True,
                    "decision": "auto_approve",
                }
            ],
        )
        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch(
                "hg_core.task_graph.fourclaw_dag_post.run_fourclaw_post_from_goal",
                return_value={
                    "ok": True,
                    "outputs": {"thread_id": "thread-42", "thread_url": "https://example.invalid/thread-42"},
                    "external_calls": 1,
                },
            ),
        ):
            out = run_task_tool("fourclaw-auto-post", {"goal": "post about agent governance"}, timeout_s=30)
        assert out is not None and out.get("ok") is True
        outputs = out.get("outputs", {})
        assert outputs.get("approval_id")
        assert outputs.get("result", {}).get("status") == "completed"
        approval = get_store().approval_get("default", outputs["approval_id"])
        assert approval is not None
        assert approval["status"] == "approved"
        assert "Auto-approved by policy" in str(approval.get("resolution_note") or "")


def test_social_write_pending_approval_sends_queue_notification(monkeypatch):
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        db_path = root / "gateway.sqlite3"
        monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
        monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
        monkeypatch.setenv("HG_ENABLE_LIVE_SOCIAL_APIS", "1")
        monkeypatch.setenv("HG_FORCE_SOCIAL_WRITE_APPROVAL", "1")
        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch("hg_gateway.approval_notifications.notify_approval_created") as mock_notify,
        ):
            out = run_task_tool("fourclaw-auto-post", {"goal": "post about agent governance"}, timeout_s=30)
        assert out is not None and out.get("ok") is True
        mock_notify.assert_called_once()
        assert mock_notify.call_args.kwargs.get("kind") == "social_write"


def test_social_write_auto_approval_sends_telegram_with_link(monkeypatch):
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        db_path = root / "gateway.sqlite3"
        monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
        monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
        monkeypatch.setenv("HG_ENABLE_LIVE_SOCIAL_APIS", "1")
        monkeypatch.setenv("HG_OPERATOR_TENANT_ID", "default")
        from hg_gateway import store as store_module

        store_module._store = None
        from hg_gateway.store import get_store

        get_store().tenant_settings_upsert(
            "default",
            approval_rules=[
                {
                    "id": "rule-fourclaw-posts",
                    "label": "Auto approve Fourclaw auto posts",
                    "kinds": ["social_write"],
                    "risks": ["high"],
                    "workflow_ids": ["fourclaw-auto-post"],
                    "platforms": ["fourclaw"],
                    "modes": ["post"],
                    "enabled": True,
                    "decision": "auto_approve",
                }
            ],
        )
        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch(
                "hg_core.task_graph.fourclaw_dag_post.run_fourclaw_post_from_goal",
                return_value={
                    "ok": True,
                    "outputs": {"thread_id": "thread-42", "thread_url": "https://example.invalid/thread-42"},
                    "external_calls": 1,
                },
            ),
            patch("hg_gateway.approval_notifications.notify_social_auto_approved") as mock_notify,
        ):
            out = run_task_tool("fourclaw-auto-post", {"goal": "post about agent governance"}, timeout_s=30)
        assert out is not None and out.get("ok") is True
        mock_notify.assert_called_once()
        assert mock_notify.call_args.kwargs.get("thread_url") == "https://example.invalid/thread-42"


def test_moltbook_auto_post_extracts_post_url_from_script_payload(monkeypatch):
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        db_path = root / "gateway.sqlite3"
        monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
        monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
        monkeypatch.setenv("HG_ENABLE_LIVE_SOCIAL_APIS", "1")
        monkeypatch.setenv("HG_OPERATOR_TENANT_ID", "default")
        from hg_gateway import store as store_module

        store_module._store = None
        from hg_gateway.store import get_store

        get_store().tenant_settings_upsert(
            "default",
            approval_rules=[
                {
                    "id": "rule-moltbook-posts",
                    "label": "Auto approve Moltbook auto posts",
                    "kinds": ["social_write"],
                    "risks": ["high"],
                    "workflow_ids": ["moltbook-auto-post"],
                    "platforms": ["moltbook"],
                    "modes": ["post"],
                    "enabled": True,
                    "decision": "auto_approve",
                }
            ],
        )
        fake_payload = {
            "ok": True,
            "post_id": "post-42",
            "post_url": "https://www.moltbook.com/post/post-42",
            "title": "hello",
        }
        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch(
                "hg_core.task_graph.native_task_tools._run",
                return_value=CompletedProcess(args=[], returncode=0, stdout=json.dumps(fake_payload), stderr=""),
            ),
            patch("hg_gateway.approval_notifications.notify_social_auto_approved") as mock_notify,
        ):
            out = run_task_tool("moltbook-auto-post", {"goal": "post about something"}, timeout_s=30)
        assert out is not None and out.get("ok") is True
        outputs = out.get("outputs", {})
        assert outputs.get("thread_url") == "https://www.moltbook.com/post/post-42"
        assert outputs.get("result", {}).get("thread_url") == "https://www.moltbook.com/post/post-42"
        mock_notify.assert_called_once()
        assert mock_notify.call_args.kwargs.get("thread_url") == "https://www.moltbook.com/post/post-42"


def test_moltbook_engage_auto_approve_calls_post_moltbook_comment_and_returns_completed(monkeypatch):
    """Auto-approved Moltbook engage reply must call post_moltbook_comment.py (not engage_async) so the comment is actually posted."""
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        db_path = root / "gateway.sqlite3"
        monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
        monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
        monkeypatch.setenv("HG_ENABLE_LIVE_SOCIAL_APIS", "1")
        monkeypatch.setenv("HG_OPERATOR_TENANT_ID", "default")
        from hg_gateway import store as store_module

        store_module._store = None
        from hg_gateway.store import get_store

        get_store().tenant_settings_upsert(
            "default",
            approval_rules=[
                {
                    "id": "rule-moltbook-engage",
                    "label": "Auto approve Moltbook engages",
                    "kinds": ["social_write"],
                    "risks": ["high"],
                    "workflow_ids": ["moltbook-engage"],
                    "platforms": ["moltbook"],
                    "modes": ["reply"],
                    "enabled": True,
                    "decision": "auto_approve",
                }
            ],
        )
        fake_payload = {"ok": True, "post_id": "abc", "url": "https://www.moltbook.com/post/abc"}
        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch("hg_core.task_graph.native_task_tools._pick_thread_target", return_value=({"slug": "general"}, "abc")),
            patch("hg_core.task_graph.native_task_tools._fetch_thread_payload", return_value={"posts": []}),
            patch("hg_core.task_graph.native_task_tools._generate_engage_reply_text", return_value=("reply", "llm")),
            patch(
                "hg_core.task_graph.native_task_tools._run",
                return_value=CompletedProcess(args=[], returncode=0, stdout=json.dumps(fake_payload), stderr=""),
            ) as mock_run,
            patch("hg_gateway.approval_notifications.notify_social_auto_approved") as mock_notify,
        ):
            out = run_task_tool("moltbook-engage", {"goal": "reply about thing"}, timeout_s=30)
        assert out is not None and out.get("ok") is True
        result = out.get("outputs", {}).get("result", {})
        assert result.get("status") == "completed"
        assert result.get("thread_url") == "https://www.moltbook.com/post/abc"
        mock_notify.assert_called_once()
        # Assert we called post_moltbook_comment.py with --post_id and --content_file (not moltbook_engage_async.py)
        assert mock_run.called
        cmd = mock_run.call_args[0][0]
        cmd_str = " ".join(str(c) for c in cmd)
        assert "post_moltbook_comment" in cmd_str
        assert "--post_id" in cmd_str
        assert "--content_file" in cmd_str


def test_execute_social_write_approval_rejects_expired_entity_approval(monkeypatch):
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        db_path = root / "gateway.sqlite3"
        monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
        monkeypatch.setenv("HG_OPERATOR_TENANT_ID", "default")
        approval = ApprovalService(db_path=str(db_path)).create_request(
            entity_id="fourclaw-auto-post",
            action_kind="social_write",
            preview_json={"summary": "review me", "release_window_hours": 1},
            tenant_id="default",
            workflow_id="fourclaw-auto-post",
            target_platform="fourclaw",
        )
        ApprovalService(db_path=str(db_path)).approve(
            approval["approval_id"],
            tenant_id="default",
            decided_by="operator",
            decision_note="looks good",
        )
        with get_connection(str(db_path)) as conn:
            conn.execute(
                "UPDATE approval_requests SET decided_at = datetime('now', '-3 hours') WHERE approval_id = ?",
                (approval["approval_id"],),
            )
        with patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root):
            result = execute_social_write_approval(
                {
                    "task_name": "fourclaw-auto-post",
                    "platform": "fourclaw",
                    "mode": "post",
                    "draft_title": "title",
                    "draft_content": "body",
                    "entity_approval_id": approval["approval_id"],
                    "release_window_hours": 1,
                }
            )
        assert result["ok"] is False
        assert result["error"] == "social approval expired"
        assert result["outputs"]["result"]["status"] == "expired"
        log_path = Path(result["outputs"]["notification_log"])
        assert log_path.exists()
        entries = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        latest = entries[-1]
        assert latest["kind"] == "review_handoff_release_expired"
        assert latest["message"] == "fourclaw-auto-post review approval expired before release"
        assert latest["summary"]["execution"]["blocked_reason"] == "approval_expired"
        assert latest["summary"]["review_handoff"]["approval_id"] == approval["approval_id"]
        assert latest["summary"]["review_handoff"]["release_window_hours"] == 1
        assert latest["summary"]["review_handoff"]["approved_until"] == result["outputs"]["approved_until"]


def test_execute_social_write_approval_blocks_when_lane_held():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        operational_dir = root / "memory" / "automation" / "automation-underling-chan"
        operational_dir.mkdir(parents=True, exist_ok=True)
        (operational_dir / "agency_control.json").write_text(
            json.dumps({"mode": "held", "reason": "manual freeze", "updated_by": "operator"}),
            encoding="utf-8",
        )
        with patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root):
            result = execute_social_write_approval(
                {
                    "task_name": "fourclaw-auto-post",
                    "platform": "fourclaw",
                    "mode": "post",
                    "draft_title": "title",
                    "draft_content": "body",
                    "entity_approval_id": "approval-123",
                }
            )
        assert result["ok"] is False
        assert result["error"] == "agency_control_held"
        assert result["outputs"]["result"]["step"] == "approval_release_hold"
        assert result["outputs"]["agency_control_summary"]["effective_mode"] == "held"
        log_path = Path(result["outputs"]["notification_log"])
        assert log_path.exists()
        entries = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        latest = entries[-1]
        assert latest["kind"] == "agency_gate"
        assert latest["summary"]["execution"]["blocked_reason"] == "approval_release_held"
        assert latest["summary"]["review_handoff"]["approval_id"] == "approval-123"


def test_execute_social_write_approval_blocks_when_outbound_budget_exhausted():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        operational_dir = root / "memory" / "automation" / "automation-underling-chan"
        operational_dir.mkdir(parents=True, exist_ok=True)
        (operational_dir / "agency_control.json").write_text(
            json.dumps(
                {
                    "mode": "normal",
                    "reason": "daily cap reached",
                    "updated_by": "operator",
                    "daily_outbound_budget": 1,
                    "outbound_actions_window_hours": 24,
                }
            ),
            encoding="utf-8",
        )
        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch(
                "operator_console.server.app.services.operational_agency_control._recent_outbound_budget_usage",
                return_value=(1, "2026-03-13T00:00:00Z"),
            ),
        ):
            result = execute_social_write_approval(
                {
                    "task_name": "fourclaw-auto-post",
                    "platform": "fourclaw",
                    "mode": "post",
                    "draft_title": "title",
                    "draft_content": "body",
                    "entity_approval_id": "approval-456",
                }
            )
        assert result["ok"] is False
        assert result["error"] == "agency_outbound_budget_exhausted"
        assert result["outputs"]["result"]["step"] == "approval_release_outbound_budget"
        assert result["outputs"]["agency_control_summary"]["outbound_budget_exhausted"] is True
        log_path = Path(result["outputs"]["notification_log"])
        assert log_path.exists()
        entries = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        latest = entries[-1]
        assert latest["kind"] == "agency_gate"
        assert latest["summary"]["execution"]["blocked_reason"] == "approval_release_outbound_budget_exhausted"
        assert latest["summary"]["review_handoff"]["approval_id"] == "approval-456"


def test_execute_social_write_approval_blocks_when_continuity_recovery_is_blocked(monkeypatch):
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        db_path = root / "gateway.sqlite3"
        monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
        from hg_gateway import keystore_repo
        from hg_core.security.social_account_artifacts import record_social_account_session_binding

        keystore_repo.social_account_create(
            social_account_id="acct-underling-fourclaw",
            tenant_id="default",
            platform="fourclaw",
            account_alias="underling-fourclaw",
            entity_scope="underling-chan",
            persona_scope="underling_chan_operational",
            state="verified",
            db_path=str(db_path),
        )
        with get_connection(str(db_path)) as conn:
            conn.execute(
                """INSERT INTO browser_sessions (browser_session_id, tenant_id, entity_id, platform, state, started_at)
                   VALUES (?, ?, ?, ?, ?, datetime('now'))""",
                ("session-bad", "default", "underling-chan", "fourclaw", "degraded"),
            )
            conn.execute(
                """INSERT INTO proof_artifacts (proof_id, related_kind, related_id, artifact_type, path, metadata_json, created_at)
                   VALUES (?, 'browser_session', ?, 'session_degraded', ?, ?, datetime('now'))""",
                ("proof-bad", "session-bad", "missing_restart_critical_browser_artifacts", '{"reason":"missing_restart_critical_browser_artifacts"}'),
            )
        record_social_account_session_binding(
            "acct-underling-fourclaw",
            browser_session_id="session-bad",
            platform="fourclaw",
            tenant_id="default",
            entity_id="underling-chan",
            account_alias="underling-fourclaw",
            state="active",
        )
        with patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root):
            result = execute_social_write_approval(
                {
                    "task_name": "fourclaw-auto-post",
                    "platform": "fourclaw",
                    "mode": "post",
                    "draft_title": "title",
                    "draft_content": "body",
                    "entity_approval_id": "approval-789",
                }
            )
        assert result["ok"] is False
        assert result["error"] == "continuity_recovery_blocked"
        assert result["outputs"]["result"]["step"] == "approval_release_continuity_recovery"
        log_path = Path(result["outputs"]["notification_log"])
        assert log_path.exists()
        entries = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        latest = entries[-1]
        assert latest["kind"] == "agency_gate"
        assert latest["summary"]["execution"]["blocked_reason"] == "approval_release_continuity_recovery_blocked"
        assert latest["summary"]["review_handoff"]["approval_id"] == "approval-789"


def test_execute_social_write_approval_blocks_when_continuity_recovery_ack_is_required(monkeypatch):
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        db_path = root / "gateway.sqlite3"
        monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
        from hg_gateway import keystore_repo
        from hg_core.security.social_account_artifacts import record_social_account_session_binding

        keystore_repo.social_account_create(
            social_account_id="acct-underling-fourclaw",
            tenant_id="default",
            platform="fourclaw",
            account_alias="underling-fourclaw",
            entity_scope="underling-chan",
            persona_scope="underling_chan_operational",
            state="verified",
            db_path=str(db_path),
        )
        record_social_account_session_binding(
            "acct-underling-fourclaw",
            browser_session_id="session-bad",
            platform="fourclaw",
            tenant_id="default",
            entity_id="underling-chan",
            account_alias="underling-fourclaw",
            state="degraded",
        )
        record_social_account_session_binding(
            "acct-underling-fourclaw",
            browser_session_id="session-good",
            platform="fourclaw",
            tenant_id="default",
            entity_id="underling-chan",
            account_alias="underling-fourclaw",
            state="active",
        )
        profile_dir = root / "browser-profile"
        profile_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = root / "browser.png"
        screenshot_path.write_text("ok", encoding="utf-8")
        snapshot_path = root / "browser-state.json"
        snapshot_path.write_text("{}", encoding="utf-8")
        trace_path = root / "browser.zip"
        trace_path.write_text("trace", encoding="utf-8")
        with get_connection(str(db_path)) as conn:
            conn.execute("""INSERT INTO browser_sessions (browser_session_id, tenant_id, entity_id, platform, state, started_at) VALUES (?, ?, ?, ?, ?, '2026-03-13T23:00:00Z')""",("session-bad","default","underling-chan","fourclaw","degraded"))
            conn.execute("""INSERT INTO browser_sessions (browser_session_id, tenant_id, entity_id, platform, state, started_at, trace_path, latest_screenshot_path) VALUES (?, ?, ?, ?, ?, '2026-03-14T01:30:00Z', ?, ?)""",("session-good","default","underling-chan","fourclaw","active",str(trace_path),str(screenshot_path)))
            conn.execute("""INSERT INTO proof_artifacts (proof_id, related_kind, related_id, artifact_type, path, metadata_json, created_at) VALUES (?, 'browser_session', ?, 'snapshot', ?, ?, '2026-03-14T01:30:10Z')""",("proof-snapshot","session-good",str(snapshot_path),'{}'))
            conn.execute("""INSERT INTO proof_artifacts (proof_id, related_kind, related_id, artifact_type, path, metadata_json, created_at) VALUES (?, 'browser_session', ?, 'profile_dir', ?, ?, '2026-03-14T01:30:05Z')""",("proof-profile","session-good",str(profile_dir),'{}'))
            conn.execute("""INSERT INTO proof_artifacts (proof_id, related_kind, related_id, artifact_type, path, metadata_json, created_at) VALUES (?, 'browser_session', ?, 'session_degraded', ?, ?, '2026-03-13T23:59:59Z')""",("proof-bad","session-bad","missing_restart_critical_browser_artifacts",'{"reason":"missing_restart_critical_browser_artifacts"}'))
            conn.execute("""UPDATE proof_artifacts SET created_at = '2026-03-13T22:59:00Z' WHERE related_kind = 'social_account' AND related_id = ? AND artifact_type = 'browser_session_binding' AND path LIKE ?""",("acct-underling-fourclaw","%session-bad%"))
            conn.execute("""UPDATE proof_artifacts SET created_at = '2026-03-14T01:31:00Z' WHERE related_kind = 'social_account' AND related_id = ? AND artifact_type = 'browser_session_binding' AND path LIKE ?""",("acct-underling-fourclaw","%session-good%"))
        with patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root):
            result = execute_social_write_approval(
                {
                    "task_name": "fourclaw-auto-post",
                    "platform": "fourclaw",
                    "mode": "post",
                    "draft_title": "title",
                    "draft_content": "body",
                    "entity_approval_id": "approval-790",
                }
            )
        assert result["ok"] is False
        assert result["error"] == "continuity_recovery_ack_required"
        assert result["outputs"]["result"]["step"] == "approval_release_continuity_recovery_ack"


def test_execute_social_write_approval_blocks_when_operational_resume_checkpoint_is_required(monkeypatch):
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        db_path = root / "gateway.sqlite3"
        monkeypatch.setenv("HG_WORKSPACE", str(root))
        monkeypatch.setenv("HG_OPERATOR_TENANT_ID", "operator-runtime")
        monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
        approval_service = ApprovalService(db_path=str(db_path))
        approval = approval_service.create_request(
            entity_id="fourclaw-auto-post",
            action_kind="social_write",
            preview_json={
                "summary": "draft ready",
                "task_name": "fourclaw-auto-post",
                "platform": "fourclaw",
                "mode": "post",
            },
            tenant_id="operator-runtime",
            workflow_id="fourclaw-auto-post",
            target_platform="fourclaw",
        )
        approval_service.approve(
            approval["approval_id"],
            tenant_id="operator-runtime",
            decided_by="rev",
            decision_note="ship it",
        )
        monkeypatch.setattr(
            "hg_core.task_graph.native_task_tools._operational_resume_release_state_for_task",
            lambda task_name: {
                "required": True,
                "governance": {"status": "ready", "required_actions": []},
                "checkpoint": {
                    "approved": False,
                    "invalidated": True,
                    "invalidated_reason": "operational_resume_no_longer_ready",
                },
            },
        )
        monkeypatch.setattr(
            "hg_core.task_graph.native_task_tools._continuity_recovery_readiness_for_task",
            lambda task_name: {"status": "ready", "resume_permitted": True, "blocking": [], "cautions": []},
        )
        with patch("hg_core.task_graph.native_task_tools.run_task_tool") as run_task_tool_mock:
            result = execute_social_write_approval(
                {
                    "task_name": "fourclaw-auto-post",
                    "platform": "fourclaw",
                    "mode": "post",
                    "draft_title": "title",
                    "draft_content": "body",
                    "entity_approval_id": approval["approval_id"],
                }
            )
        assert result["ok"] is False
        assert result["error"] == "operational_resume_checkpoint_required"
        assert result["outputs"]["result"]["step"] == "approval_release_operational_resume_checkpoint"
        assert run_task_tool_mock.call_count == 0
        notification_log = Path(result["outputs"]["notification_log"])
        assert notification_log.exists()
        entries = [json.loads(line) for line in notification_log.read_text(encoding="utf-8").splitlines() if line.strip()]
        latest = entries[-1]
        assert latest["kind"] == "agency_gate"
        assert latest["summary"]["execution"]["blocked_reason"] == "approval_release_operational_resume_checkpoint_required"
        assert latest["summary"]["review_handoff"]["approval_id"] == approval["approval_id"]


def test_monitor_mode_returns_dashboard_paths():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        dashboard_dir = root / "memory" / "overseer"
        dashboard_dir.mkdir(parents=True, exist_ok=True)
        (dashboard_dir / "dashboard.png").write_bytes(b"png")
        (dashboard_dir / "dashboard_latest.pdf").write_bytes(b"%PDF")
        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch("hg_core.task_graph.native_task_tools._run_module_json", return_value={"ok": True, "payload": {"ok": True}, "stdout": "done", "returncode": 0}),
        ):
            out = run_task_tool("overseer-monitor", {"goal": ""}, timeout_s=30)
        assert out is not None and out.get("ok") is True
        outputs = out.get("outputs", {})
        assert outputs.get("dashboard_png", "").endswith("dashboard.png")
        assert outputs.get("dashboard_pdf", "").endswith("dashboard_latest.pdf")
        assert outputs.get("result", {}).get("status") == "completed"


def test_maintenance_mode_uses_entrypoint_payload():
    with patch(
        "hg_core.task_graph.native_task_tools._run_module_json",
        return_value={"ok": True, "payload": {"agents_processed": 3, "total_promoted": 7}, "stdout": "done", "returncode": 0},
    ):
        out = run_task_tool("memory-maintenance", {"goal": ""}, timeout_s=30)
    assert out is not None and out.get("ok") is True
    outputs = out.get("outputs", {})
    assert outputs.get("agents_processed") == 3
    assert outputs.get("result", {}).get("agents_processed") == 3


def test_execute_social_write_approval_blocks_when_identity_restore_validation_is_required(monkeypatch):
    monkeypatch.setattr(
        "hg_core.task_graph.native_task_tools._runtime_continuity_state_for_task",
        lambda task_name: {
            "continuity_recovery_readiness": {"status": "ready", "resume_permitted": True, "blocking": [], "cautions": []},
            "continuity_incident_summary": {"status": "clean"},
            "continuity_repair_plan": {"status": "repair_required", "open_checks": ["verify_identity_restore"], "completed_checks": []},
            "post_rebuild_continuity_check": {"status": "not_required", "verification_required": False, "verified": False},
            "required": True,
            "operational_resume_governance_summary": {"status": "caution", "required_actions": ["verify_identity_restore"]},
            "operational_resume_checkpoint": {"approved": True},
            "identity_restore_validation": {"summary": "verify_identity_restore_continuity"},
            "supervised_resume_validation": {"status": "not_required", "required": False, "validated": False},
            "bounded_autonomy_policy_summary": {"blockers": ["identity_restore_validation_required"]},
        },
    )
    with patch("hg_core.task_graph.native_task_tools.run_task_tool") as run_task_tool_mock:
        result = execute_social_write_approval(
            {
                "task_name": "fourclaw-auto-post",
                "platform": "fourclaw",
                "mode": "post",
                "draft_title": "title",
                "draft_content": "body",
                "entity_approval_id": "approval-123",
            }
        )
    assert result["ok"] is False
    assert result["error"] == "identity_restore_validation_required"
    assert result["outputs"]["result"]["step"] == "approval_release_identity_restore_validation"
    assert run_task_tool_mock.call_count == 0
    assert result["outputs"]["notification_payload"]["summary"]["identity_restore_validation"]["summary"] == "verify_identity_restore_continuity"
    assert result["outputs"]["notification_payload"]["summary"]["bounded_autonomy_policy_summary"]["blockers"] == ["identity_restore_validation_required"]


def test_run_task_tool_records_runtime_continuity_observations(monkeypatch):
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        monkeypatch.setattr(
            "hg_core.task_graph.native_task_tools._runtime_continuity_state_for_task",
            lambda task_name: {
                "continuity_incident_summary": {
                    "status": "recovered",
                    "latest_event_at": "2026-03-13T10:00:00Z",
                    "latest_event_detail": "session rebound",
                },
                "continuity_recovery_readiness": {
                    "status": "ready",
                    "safe_to_resume": True,
                    "blocking": [],
                    "cautions": [],
                },
                "continuity_repair_plan": {
                    "status": "clean",
                    "open_checks": [],
                    "completed_checks": ["verify_post_rebuild_continuity"],
                },
                "post_rebuild_continuity_check": {
                    "status": "verified",
                    "verification_required": True,
                    "verified": True,
                    "verified_at": "2026-03-13T11:00:00Z",
                },
                "identity_restore_validation": {
                    "status": "validated",
                    "required": True,
                    "verified": True,
                    "verified_at": "2026-03-13T12:00:00Z",
                },
                "supervised_resume_validation": {
                    "status": "validated",
                    "required": True,
                    "validated": True,
                    "validated_at": "2026-03-13T13:00:00Z",
                },
                "operational_resume_governance_summary": {"status": "ready"},
                "bounded_autonomy_policy_summary": {"status": "ready", "blockers": []},
            },
        )
        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch("hg_core.task_graph.native_task_tools._task_tool_auto_post", return_value={"ok": True, "outputs": {"result": {"status": "completed"}}}),
        ):
            out = run_task_tool("fourclaw-auto-post", {"goal": "post something"}, timeout_s=30)
            assert out is not None and out["ok"] is True

        log_path = root / "memory" / "automation" / "notifications" / "human_notifications.jsonl"
        assert log_path.exists()
        entries = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        kinds = [entry["kind"] for entry in entries]
        assert "continuity_runtime_observed" in kinds
        assert "post_rebuild_runtime_observed" in kinds
        assert "identity_restore_runtime_observed" in kinds
        assert "supervised_resume_runtime_observed" in kinds

        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch("hg_core.task_graph.native_task_tools._task_tool_auto_post", return_value={"ok": True, "outputs": {"result": {"status": "completed"}}}),
        ):
            out = run_task_tool("fourclaw-auto-post", {"goal": "post something"}, timeout_s=30)
            assert out is not None and out["ok"] is True
        entries_again = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(entries_again) == len(entries)


def test_sandboxed_registry_task_launch_routes_through_child_runner(monkeypatch):
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        child_payload = {
            "ok": True,
            "outputs": {"result": {"status": "completed", "task_name": "fourclaw-auto-post"}},
            "returncode": 0,
            "external_calls": 0,
        }
        sandbox_calls = {}

        def _fake_subprocess_run(cmd, **kwargs):
            sandbox_calls["cmd"] = cmd
            sandbox_calls["env"] = kwargs.get("env", {})
            return CompletedProcess(cmd, 0, stdout=json.dumps(child_payload), stderr="")

        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch("hg_core.task_graph.native_task_tools.get_job_info", return_value={"job_id": "fourclaw-auto-post", "session_target": "automation-fourclaw-auto-post", "platform": "fourclaw", "mode": "auto-post", "sandbox_mode": "sandbox"}),
            patch("hg_core.task_graph.native_task_tools.create_sandbox_context", return_value="sbx_test"),
            patch("hg_core.task_graph.native_task_tools.destroy_sandbox_context", return_value="evt_test"),
            patch("hg_core.task_graph.native_task_tools.subprocess.run", side_effect=_fake_subprocess_run),
        ):
            monkeypatch.setenv("HG_TASK_EXECUTION_SANDBOX", "1")
            out = run_task_tool("fourclaw-auto-post", {"goal": "post something"}, timeout_s=30, memory_profile="entity_recall")
        assert out is not None and out["ok"] is True
        assert out["outputs"]["result"]["status"] == "completed"
        assert sandbox_calls["env"].get("HG_TASK_SANDBOX_CHILD") == "1"
        assert sandbox_calls["env"].get("HG_MEMORY_PROFILE") == "entity_recall"
        assert "sandboxed_task_runner" in " ".join(sandbox_calls["cmd"])
        monkeypatch.delenv("HG_TASK_EXECUTION_SANDBOX", raising=False)


def test_research_mode_writes_brief_and_knowledge_file():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        def _fake_search(kind: str, *, query: str, count: int, freshness: str | None = None, method: str = "GET"):
            if kind == "news":
                return [
                    {"title": "Agent governance update", "url": "https://example.com/news", "description": "Fresh policy headline"},
                    {"title": "Inference cost shift", "url": "https://example.com/costs", "description": "Serving economics move"},
                ]
            return [
                {"title": "Topic overview", "url": "https://example.com/1", "description": "Primary explanation"},
                {"title": "Implementation guide", "url": "https://example.com/2", "description": "Hands-on guide"},
                {"title": "Reference notes", "url": "https://example.com/3", "description": "Background context"},
            ]

        with patch.dict(os.environ, {"HG_WORKSPACE": str(root), "HG_GATEWAY_DB_PATH": str(root / "memory" / "gateway.sqlite3")}):
            with (
                patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
                patch("hg_realtime.integrations.search_tools._run_brave_search", side_effect=_fake_search),
                patch("hg_knowledge.research_agent.record_research_decision", return_value=None),
            ):
                out = run_task_tool("knowledge-research-auto", {"goal": "agent governance"}, timeout_s=30)
        assert out is not None and out.get("ok") is True
        outputs = out.get("outputs", {})
        assert Path(outputs.get("brief_path", "")).exists()
        assert Path(outputs.get("knowledge_file", "")).exists()
        assert str(outputs.get("research_history", "")).startswith("db:knowledge:research_history:")
        assert outputs.get("result", {}).get("status") == "completed"


def test_research_mode_v2_uses_v2_session_dir():
    """knowledge-research-auto-v2 is supported and uses session dir automation-knowledge-research-auto-v2."""
    with TemporaryDirectory() as tmp:
        root = Path(tmp)

        def _fake_search(kind: str, *, query: str, count: int, freshness: str | None = None, method: str = "GET"):
            if kind == "news":
                return [
                    {"title": "News headline", "url": "https://example.com/news", "description": "Brief"},
                ]
            return [
                {"title": "Topic", "url": "https://example.com/1", "description": "Overview"},
            ] * 2

        with patch.dict(os.environ, {"HG_WORKSPACE": str(root), "HG_GATEWAY_DB_PATH": str(root / "memory" / "gateway.sqlite3")}):
            with (
                patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
                patch("hg_realtime.integrations.search_tools._run_brave_search", side_effect=_fake_search),
                patch("hg_knowledge.research_agent.record_research_decision", return_value=None),
            ):
                out = run_task_tool("knowledge-research-auto-v2", {"goal": "test topic"}, timeout_s=30)
            assert out is not None and out.get("ok") is True
            outputs = out.get("outputs", {})
            assert "research_history" in outputs
            assert str(outputs.get("research_history", "")).startswith("db:knowledge:research_history:")
            assert outputs.get("result", {}).get("status") == "completed"
            assert outputs.get("current_events_source_mix", {}).get("brave", 0) >= 1
            brief_files = list((root / "knowledge" / "current_events").glob("brief-*.md"))
            legacy_files = [
                path
                for path in (root / "knowledge" / "current_events").glob("*.md")
                if not path.name.startswith("brief-")
            ]
            assert brief_files
            assert legacy_files
            history = list_research_history("knowledge-research-auto-v2", limit=100)
            topics = [str(item.get("topic") or "") for item in history.get("topics_researched", []) if isinstance(item, dict)]
            assert "current events brief" in topics
            assert "test topic" in topics
            current_events_entry = next(item for item in history.get("topics_researched", []) if isinstance(item, dict) and str(item.get("topic") or "") == "current events brief")
            assert current_events_entry.get("source_mix", {}).get("brave", 0) >= 1


def test_research_run_task_tool_passes_content_hint():
    """run_task_tool for knowledge-research resolves content_hint and passes it to _task_tool_research."""
    research_out = {
        "ok": True,
        "outputs": {
            "result": {"status": "completed", "mode": "research"},
            "knowledge_files": [],
            "brief_path": "",
            "research_history": "",
        },
        "returncode": 0,
        "external_calls": 0,
    }
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch("hg_core.task_graph.native_task_tools._task_tool_research", return_value=research_out) as mock_research,
        ):
            out = run_task_tool(
                "knowledge-research-auto-v2",
                {"goal": "test goal", "content_hint": "Recently researched: A, B. Queue: 2; next: C."},
                timeout_s=30,
            )
    assert out is not None and out.get("ok") is True
    mock_research.assert_called_once()
    call_kwargs = mock_research.call_args[1]
    assert call_kwargs.get("content_hint") == "Recently researched: A, B. Queue: 2; next: C."
    assert call_kwargs.get("goal") == "test goal"


def test_research_content_hint_injected_into_result_and_first_file():
    """_task_tool_research injects content_hint into result and into first knowledge file when present."""
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "knowledge" / "current_events").mkdir(parents=True, exist_ok=True)
        (root / "knowledge" / "current_events" / "brief-2026-03-12.md").write_text("1. **Head**\n", encoding="utf-8")
        (root / "knowledge" / "general").mkdir(parents=True, exist_ok=True)

        def _fake_search(kind: str, *, query: str, count: int, freshness: str | None = None, method: str = "GET"):
            if kind == "news":
                return [{"title": "News", "url": "https://x", "description": "D"}]
            return [{"title": "Topic", "url": "https://x/1", "description": "Overview"}] * 2

        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch("hg_realtime.integrations.search_tools._run_brave_search", side_effect=_fake_search),
            patch("hg_knowledge.research_agent.record_research_decision", return_value=None),
        ):
            from hg_core.task_graph.native_task_tools import _task_tool_research

            out = _task_tool_research(
                task_name="knowledge-research-auto-v2",
                goal="single topic",
                timeout_s=30,
                content_hint="Recently researched: X. Queue: 1; next: Y.",
            )
        assert out is not None and out.get("ok") is True
        result = out.get("outputs", {}).get("result", {})
        assert result.get("content_hint_used") == "Recently researched: X. Queue: 1; next: Y."
        knowledge_files = out.get("outputs", {}).get("knowledge_files", [])
        if knowledge_files:
            first_content = Path(knowledge_files[0]).read_text(encoding="utf-8")
            assert "Current board context" in first_content
            assert "Recently researched: X" in first_content


def test_research_mode_mirrors_to_shared_store_before_disk_index(monkeypatch):
    with TemporaryDirectory() as tmp:
        root = Path(tmp)

        def _fake_search(kind: str, *, query: str, count: int, freshness: str | None = None, method: str = "GET"):
            if kind == "news":
                return [{"title": "News", "url": "https://example.com/news", "description": "Brief"}]
            return [{"title": "Topic", "url": "https://example.com/1", "description": "Overview"}] * 2

        mirror_calls: list[dict[str, str]] = []
        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch("hg_realtime.integrations.search_tools._run_brave_search", side_effect=_fake_search),
            patch("hg_knowledge.research_agent.record_research_decision", return_value=None),
            patch("hg_core.task_graph.native_task_tools._mirror_knowledge_document", side_effect=lambda **kwargs: mirror_calls.append(kwargs) or True),
            patch("hg_core.task_graph.native_task_tools._index_knowledge_file") as mock_index,
        ):
            out = run_task_tool("knowledge-research-auto", {"goal": "agent governance"}, timeout_s=30)
        assert out is not None and out.get("ok") is True
        assert mirror_calls
        assert any(call.get("relative_path", "").startswith("knowledge/") for call in mirror_calls)
        mock_index.assert_not_called()


def test_research_mode_falls_back_to_disk_index_when_shared_mirror_fails(monkeypatch):
    with TemporaryDirectory() as tmp:
        root = Path(tmp)

        def _fake_search(kind: str, *, query: str, count: int, freshness: str | None = None, method: str = "GET"):
            if kind == "news":
                return [{"title": "News", "url": "https://example.com/news", "description": "Brief"}]
            return [{"title": "Topic", "url": "https://example.com/1", "description": "Overview"}] * 2

        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch("hg_realtime.integrations.search_tools._run_brave_search", side_effect=_fake_search),
            patch("hg_knowledge.research_agent.record_research_decision", return_value=None),
            patch("hg_core.task_graph.native_task_tools._mirror_knowledge_document", return_value=False),
            patch("hg_core.task_graph.native_task_tools._index_knowledge_file") as mock_index,
        ):
            out = run_task_tool("knowledge-research-auto", {"goal": "agent governance"}, timeout_s=30)
        assert out is not None and out.get("ok") is True
        assert mock_index.call_count >= 1


def test_headline_candidates_from_brief_dedupes_duplicate_titles():
    with TemporaryDirectory() as tmp:
        brief = Path(tmp) / "brief-2026-03-09.md"
        brief.write_text(
            "\n".join(
                [
                    "# Current Events Brief",
                    "1. **Stock market news for March 6, 2026** - https://a.example [Business]",
                    "2. **Stock market news for March 6, 2026** - https://b.example [Finance]",
                    "3. **Stormy space weather may be garbling messages from aliens** - https://c.example [Science]",
                ]
            ),
            encoding="utf-8",
        )
        candidates = _headline_candidates_from_brief(brief)
        assert len(candidates) == 2
        assert candidates[0]["title"] == "Stock market news for March 6, 2026"


def test_topic_selection_guidance_surfaces_fresh_candidates_and_fatigued_titles():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        posts_dir = root / "memory" / "automation" / "automation-fourclaw-auto-post"
        posts_dir.mkdir(parents=True, exist_ok=True)
        (root / "knowledge" / "current_events").mkdir(parents=True, exist_ok=True)
        (root / "knowledge" / "current_events" / "brief-2026-03-09.md").write_text(
            "\n".join(
                [
                    "# Current Events Brief",
                    "1. **Oil prices surge after regional war shock** - https://example.com/oil [Business]",
                    "2. **Stormy space weather may be garbling messages from aliens** - https://example.com/space [Science]",
                ]
            ),
            encoding="utf-8",
        )
        (posts_dir / "posts.json").write_text(
            json.dumps(
                {
                    "posts": [
                        {"title": "why do secure AI agents always feel like ticking bombs?", "timestamp": "2026-03-09T01:00:00Z"},
                        {"title": "they said secure your AI like it is a checkbox", "timestamp": "2026-03-09T02:00:00Z"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        guidance = _topic_selection_guidance(root, platform="fourclaw", task_name="fourclaw-auto-post")
        assert "Fresh candidate directions:" in guidance
        assert "Oil prices surge after regional war shock" in guidance
        assert "Avoid repeating these recently overused themes or angles:" in guidance
        assert "secure AI agents" in guidance


def test_select_research_work_items_returns_up_to_eight_items():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        with patch.dict(os.environ, {"HG_WORKSPACE": str(root), "HG_GATEWAY_DB_PATH": str(root / "memory" / "gateway.sqlite3")}):
            items = _select_research_work_items(root, "knowledge-research-auto-v2")
        assert 1 <= len(items) <= 8
        topics = {item["topic"] for item in items}
        assert len(topics) == len(items)


def test_select_research_work_items_prefers_empty_category():
    """When a category has no .md files (empty), it is chosen before stale categories with files."""
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "knowledge" / "economics").mkdir(parents=True, exist_ok=True)
        (root / "knowledge" / "economics" / "business.md").write_text("# Business", encoding="utf-8")
        (root / "knowledge" / "health").mkdir(parents=True, exist_ok=True)
        items = _select_research_work_items(root, "knowledge-research-auto-v2")
        domain_categories = [item.get("category") for item in items if item.get("source") == "domain"]
        assert "health" in domain_categories
        assert "economics" not in domain_categories


def test_select_research_work_items_excludes_headline_like_queue_topics():
    """When the queue contains only headline-like topics, work items are domain-only (no queue topics)."""
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "knowledge" / "general").mkdir(parents=True, exist_ok=True)
        with patch.dict(os.environ, {"HG_WORKSPACE": str(root), "HG_GATEWAY_DB_PATH": str(root / "memory" / "gateway.sqlite3")}):
            with patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root):
                queue_topic("Why every emerging power in the world is failing to coordinate on Iran", requested_by="test")
                queue_topic("BRICS bickering over Iran geopol and nobody can agree on anything", requested_by="test")
            items = _select_research_work_items(root, "knowledge-research-auto-v2")
        queue_sources = [item for item in items if item.get("source") == "queue"]
        assert len(queue_sources) == 0
        topics_lower = [str(item.get("topic") or "").strip().lower() for item in items]
        assert "why every emerging power" not in " ".join(topics_lower)
        assert "brics bickering" not in " ".join(topics_lower)
        domain_items = [item for item in items if item.get("source") == "domain"]
        assert len(domain_items) >= 1


def test_select_research_work_items_includes_short_valid_queue_topic():
    """A short, valid queue topic (e.g. Health) still appears in work items; headline-like one does not."""
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "knowledge" / "general").mkdir(parents=True, exist_ok=True)
        with patch.dict(os.environ, {"HG_WORKSPACE": str(root), "HG_GATEWAY_DB_PATH": str(root / "memory" / "gateway.sqlite3")}):
            with patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root):
                queue_topic("Health", requested_by="test")
                queue_topic("Why every emerging power in the world is failing to coordinate", requested_by="test")
            items = _select_research_work_items(root, "knowledge-research-auto-v2")
        topics = [str(item.get("topic") or "").strip() for item in items]
        assert "Health" in topics
        assert not any("why every emerging power" in t.lower() for t in topics)


def test_select_research_work_items_entity_requested_first():
    """Work items from queue list entity-requested (or high-priority) first (T5)."""
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "knowledge" / "general").mkdir(parents=True, exist_ok=True)
        with patch.dict(os.environ, {"HG_WORKSPACE": str(root), "HG_GATEWAY_DB_PATH": str(root / "memory" / "gateway.sqlite3")}):
            with patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root):
                queue_topic("Philosophy", requested_by="", priority="medium")
                queue_topic("Mental health", requested_by="entity-1", priority="high")
            items = _select_research_work_items(root, "knowledge-research-auto-v2")
        queue_items = [i for i in items if i.get("source") == "queue"]
        assert len(queue_items) >= 1
        first_queue = queue_items[0]
        assert first_queue.get("topic") == "Mental health"
        assert (first_queue.get("requested_by") or "").strip() == "entity-1"
        assert (first_queue.get("priority") or "").strip().lower() == "high"


def test_is_headline_like_detects_long_and_markers():
    assert _is_headline_like("Oil's back stabbin' the green utopians while the world gags on fake woke energy")
    assert _is_headline_like("Title: lfg 💎 OP: mint")
    assert _is_headline_like("Something happened and then...")
    assert not _is_headline_like("Health")
    assert not _is_headline_like("Philosophy")
    assert not _is_headline_like("Business")


def test_short_topic_label_caps_length_and_handles_headlines():
    assert _short_topic_label("Health", "health") == "health"
    assert _short_topic_label("Philosophy", "philosophy") == "philosophy"
    long_headline = "Oil's back stabbin' the green utopians while the world gags on fake woke energy fantasies"
    label = _short_topic_label(long_headline, "general")
    assert len(label) <= 40
    assert "oil" in label or "general" in label


def test_knowledge_file_slug_short_and_stable():
    slug = _knowledge_file_slug("Health", "health", None)
    assert len(slug) <= 46
    assert slug == "health"
    slug_long = _knowledge_file_slug(
        "Oil's back stabbin' the green utopians while the world gags on fake woke energy fantasies",
        "general",
        "2026-03-11",
    )
    assert len(slug_long) <= 46
    assert len(slug_long + ".md") <= 50
    assert "2026-03-11" in slug_long


def test_research_mode_produces_short_knowledge_filenames():
    """Even with headline-like topic, knowledge file path segment is <= 50 chars."""
    with TemporaryDirectory() as tmp:
        root = Path(tmp)

        def _fake_search(kind: str, *, query: str, count: int, freshness: str | None = None, method: str = "GET"):
            if kind == "news":
                return [{"title": "News", "url": "https://example.com", "description": "Brief"}]
            return [{"title": "Topic", "url": "https://example.com/1", "description": "Overview"}] * 3

        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch("hg_realtime.integrations.search_tools._run_brave_search", side_effect=_fake_search),
            patch("hg_knowledge.research_agent.record_research_decision", return_value=None),
        ):
            long_goal = "Oil's back stabbin' the green utopians while the world gags on fake woke energy fantasies so the world spent decades pre"
            out = run_task_tool("knowledge-research-auto-v2", {"goal": long_goal}, timeout_s=30)
        assert out is not None and out.get("ok") is True
        knowledge_files = out.get("outputs", {}).get("knowledge_files", [])
        assert knowledge_files
        for path_str in knowledge_files:
            path = Path(path_str)
            assert len(path.name) <= 50, f"knowledge file name must be <= 50 chars: {path.name}"


def test_research_entity_requested_produces_main_plus_subtopic_files():
    """With one entity-requested topic in queue, run produces main + at least one sub-topic file in same category (T6)."""
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "knowledge" / "general").mkdir(parents=True, exist_ok=True)

        def _fake_search(kind: str, *, query: str, count: int, freshness: str | None = None, method: str = "GET"):
            if kind == "news":
                return [{"title": "News", "url": "https://example.com", "description": "Brief"}]
            return [
                {"title": "Mental health and wellness", "url": "https://example.com/1", "snippet": "Content about mental health."},
                {"title": "Vaccines and immunization", "url": "https://example.com/2", "snippet": "Content about vaccines."},
            ] * 2

        with (
            patch.dict(os.environ, {"HG_WORKSPACE": str(root)}),
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch("hg_realtime.integrations.search_tools._run_brave_search", side_effect=_fake_search),
            patch("hg_knowledge.research_agent.record_research_decision", return_value=None),
        ):
            queue_topic("Health", requested_by="entity-1", priority="high")
            out = run_task_tool("knowledge-research-auto-v2", {"goal": ""}, timeout_s=60)
        assert out is not None and out.get("ok") is True
        knowledge_files = out.get("outputs", {}).get("knowledge_files", [])
        assert len(knowledge_files) >= 2
        assert out.get("outputs", {}).get("current_events_source_mix", {}).get("brave", 0) >= 1
        categories = {str(Path(p).parent.name) for p in knowledge_files}
        assert len(categories) >= 1
        health_paths = [p for p in knowledge_files if "health" in Path(p).parent.name.lower()]
        assert len(health_paths) >= 2
        from hg_gateway.operational_state_ledger import load_operational_json_state

        deliveries = load_operational_json_state(root, state_key="research_deliveries").get("payload") or {}
        delivery_topics = [str(item.get("topic") or "") for item in deliveries.get("deliveries", []) if isinstance(item, dict)]
        assert "Health" in delivery_topics


def test_knowledge_context_summary_includes_headlines():
    """_knowledge_context_summary returns snippet from brief; shuffles headline order."""
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "knowledge" / "current_events").mkdir(parents=True, exist_ok=True)
        (root / "knowledge" / "current_events" / "brief-2026-03-11.md").write_text(
            "\n".join(
                [
                    "# Current Events Brief",
                    "",
                    "## Headlines",
                    "",
                    "1. **First headline** - https://a.com [Tech]",
                    "2. **Second headline** - https://b.com [Science]",
                ]
            ),
            encoding="utf-8",
        )
        summary = _knowledge_context_summary(root)
        assert "Knowledge context" in summary
        assert "brief-2026-03-11" in summary
        assert "First headline" in summary or "Second headline" in summary


def test_create_social_write_approval_retries_locked_db(monkeypatch):
    import hg_core.task_graph.native_task_tools as ntt

    class _FakeStore:
        def __init__(self):
            self.calls = 0
            self.last_args = None

        def approval_add(self, *args, **kwargs):
            self.calls += 1
            self.last_args = args
            if self.calls < 2:
                raise RuntimeError("database is locked")
            return "approval-123"

    store = _FakeStore()
    monkeypatch.setenv("HG_OPERATOR_TENANT_ID", "operator-runtime")
    with patch("hg_gateway.store.get_store", return_value=store):
        aid = ntt._create_social_write_approval(
            task_name="fourclaw-auto-post",
            platform="fourclaw",
            mode="post",
            title="Approve fourclaw post",
            content="body",
            draft_artifact="draft.json",
        )
    assert aid == "approval-123"
    assert store.calls == 2
    assert store.last_args is not None
    assert store.last_args[0] == "operator-runtime"
    assert store.last_args[6]["workflow_id"] == "fourclaw-auto-post"
    assert store.last_args[6]["graph_id"] == "fourclaw-auto-post"


# --- Browse-before-post (auto-post content_hint / goal_for_execution) ---


def test_generate_post_draft_text_without_content_hint_omits_feed_context(monkeypatch):
    """With content_hint empty, user prompt must not contain 'Recent feed/thread context'."""
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        captured_messages = []

        def _capture_llm(messages, **kwargs):
            captured_messages.append(messages)
            return "Test Title\nTest body content"

        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch("hg_core.task_graph.native_task_tools._llm_complete", side_effect=_capture_llm),
        ):
            _generate_post_draft_text(
                task_name="moltbook-auto-post",
                platform="moltbook",
                goal="post something",
                content_hint="",
            )
        assert len(captured_messages) == 1
        user_content = next((m.get("content", "") for m in captured_messages[0] if m.get("role") == "user"), "")
        assert "Recent feed/thread context" not in user_content


def test_generate_post_draft_text_with_content_hint_includes_feed_context(monkeypatch):
    """With non-empty content_hint, user prompt must include 'Recent feed/thread context' and the hint."""
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        captured_messages = []

        def _capture_llm(messages, **kwargs):
            captured_messages.append(messages)
            return "Title\nBody"

        hint = "Recent feed: Alice: Hello | Bob: World"
        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch("hg_core.task_graph.native_task_tools._llm_complete", side_effect=_capture_llm),
        ):
            _generate_post_draft_text(
                task_name="moltbook-auto-post",
                platform="moltbook",
                goal="post something",
                content_hint=hint,
            )
        assert len(captured_messages) == 1
        user_content = next((m.get("content", "") for m in captured_messages[0] if m.get("role") == "user"), "")
        assert "Recent feed/thread context" in user_content
        assert "Alice: Hello" in user_content


def test_run_task_tool_auto_post_passes_content_hint_and_goal_for_execution(monkeypatch):
    """run_task_tool for auto-post with content_hint and goal_for_execution passes them to draft generation."""
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        draft_calls = []

        def _capture_draft(*args, **kwargs):
            draft_calls.append({"args": args, "kwargs": kwargs})
            return PostDraftResult(
                action="post",
                title="Title",
                body="Body content",
                reason="",
                lifecycle={"soul": "", "heart": "", "identity": ""},
                generation_source="llm",
            )

        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch("hg_core.task_graph.native_task_tools._live_social_enabled", return_value=False),
            patch(
                "hg_core.task_graph.native_task_tools._generate_post_draft_text",
                side_effect=_capture_draft,
            ),
        ):
            run_task_tool(
                "moltbook-auto-post",
                {
                    "goal": "original goal",
                    "content_hint": "Recent feed: something",
                    "goal_for_execution": "refined goal with context",
                },
                timeout_s=30,
            )
        assert len(draft_calls) == 1
        assert draft_calls[0]["kwargs"].get("content_hint") == "Recent feed: something"
        assert draft_calls[0]["kwargs"].get("goal") == "original goal"


def test_run_task_tool_auto_post_treats_unresolved_refs_as_empty(monkeypatch):
    """When content_hint or goal_for_execution look like $node refs, they are treated as empty; goal is used."""
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        draft_calls = []

        def _capture_draft(*args, **kwargs):
            draft_calls.append({"kwargs": kwargs})
            return PostDraftResult(
                action="post",
                title="Title",
                body="Body",
                reason="",
                lifecycle={"soul": "", "heart": "", "identity": ""},
                generation_source="llm",
            )

        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch("hg_core.task_graph.native_task_tools._live_social_enabled", return_value=False),
            patch(
                "hg_core.task_graph.native_task_tools._generate_post_draft_text",
                side_effect=_capture_draft,
            ),
        ):
            run_task_tool(
                "moltbook-auto-post",
                {
                    "goal": "test goal",
                    "content_hint": "$node.read_content_queue.content_hint",
                    "goal_for_execution": "$node.draft_candidates.goal_for_execution",
                },
                timeout_s=30,
            )
        assert len(draft_calls) == 1
        assert draft_calls[0]["kwargs"].get("content_hint") == ""
        assert draft_calls[0]["kwargs"].get("goal") == "test goal"


# --- Moltstack DAG native handlers (publish / draft) ---


def test_run_task_tool_moltstack_publish_returns_not_none_with_empty_queue(monkeypatch):
    """run_task_tool('moltstack-publish', ...) returns a dict with outputs.result when script reports empty queue."""
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        script_path = root / "moltstack" / "moltstack_publish_post_async.py"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text("# stub", encoding="utf-8")
        empty_queue_result = {
            "ok": False,
            "action": "publish_post",
            "error": "Queue is empty",
            "message": "No posts in queue to publish",
        }
        fake_process = CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(empty_queue_result, ensure_ascii=False),
            stderr="",
        )
        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch("hg_core.task_graph.native_task_tools._run", return_value=fake_process),
        ):
            out = run_task_tool("moltstack-publish", {}, timeout_s=30)
        assert out is not None
        assert "outputs" in out
        result = out["outputs"].get("result") or {}
        assert result.get("action") == "publish_post"
        assert result.get("error") == "Queue is empty"
        assert out.get("returncode") == 0


def test_run_task_tool_moltstack_publish_parses_rate_limited_output(monkeypatch):
    """run_task_tool('moltstack-publish', ...) parses rate_limited JSON from script stdout."""
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        script_path = root / "moltstack" / "moltstack_publish_post_async.py"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text("# stub", encoding="utf-8")
        rate_limited_result = {
            "ok": False,
            "action": "publish_post",
            "error": "rate_limited",
            "hours_remaining": 12.5,
            "message": "Rate limit active: 12.5h remaining until next post",
        }
        fake_process = CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(rate_limited_result, ensure_ascii=False),
            stderr="",
        )
        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch("hg_core.task_graph.native_task_tools._run", return_value=fake_process),
        ):
            out = run_task_tool("moltstack-publish", {}, timeout_s=30)
        assert out is not None
        result = out["outputs"].get("result") or {}
        assert result.get("action") == "publish_post"
        assert result.get("error") == "rate_limited"
        assert result.get("hours_remaining") == 12.5


def test_run_task_tool_moltstack_draft_returns_structured_result_when_script_succeeds(monkeypatch):
    """run_task_tool('moltstack-draft', ...) returns outputs.result with action/queue_size when draft script succeeds."""
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        script_path = root / "moltstack" / "moltstack_draft_post_async.py"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text("# stub", encoding="utf-8")
        script_success = {
            "ok": True,
            "action": "add_to_queue",
            "queue_size": 1,
        }
        fake_process = CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(script_success, ensure_ascii=False),
            stderr="",
        )
        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch(
                "hg_core.task_graph.native_task_tools._generate_moltstack_draft_text",
                return_value=("Test Title", "x " * 800 + "https://example.com/source\n\n" * 5, "general"),
            ),
            patch("hg_core.task_graph.native_task_tools._run", return_value=fake_process),
        ):
            out = run_task_tool("moltstack-draft", {"goal": "test topic"}, timeout_s=60)
        assert out is not None
        result = out["outputs"].get("result") or {}
        assert result.get("action") == "add_to_queue"
        assert result.get("queue_size") == 1
        assert out.get("returncode") == 0


def test_run_task_tool_moltstack_draft_returns_structured_result_when_validation_fails(monkeypatch):
    """run_task_tool('moltstack-draft', ...) returns outputs.result with quality_score/validation_errors when script fails."""
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        script_path = root / "moltstack" / "moltstack_draft_post_async.py"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text("# stub", encoding="utf-8")
        validation_fail = {
            "ok": False,
            "action": "draft_post",
            "error": "Quality validation failed",
            "quality_score": 7.5,
            "validation_errors": ["Content too short: 100 words (minimum 1500)"],
        }
        fake_process = CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr=json.dumps(validation_fail, ensure_ascii=False),
        )
        with (
            patch("hg_core.task_graph.native_task_tools.get_workspace_root", return_value=root),
            patch(
                "hg_core.task_graph.native_task_tools._generate_moltstack_draft_text",
                return_value=("Title", "short content", "general"),
            ),
            patch("hg_core.task_graph.native_task_tools._run", return_value=fake_process),
        ):
            out = run_task_tool("moltstack-draft", {"goal": "test"}, timeout_s=60)
        assert out is not None
        assert out.get("ok") is False
        result = out["outputs"].get("result") or {}
        assert result.get("action") == "draft_post"
        assert result.get("quality_score") == 7.5
        assert out.get("returncode") == 1
