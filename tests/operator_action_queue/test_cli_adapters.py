"""CLI and adapter tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from hg_runtime.exciton_action_model.action_types import AgentActionType
from hg_runtime.operator_action_queue.adapters import from_social_review_item, to_social_review_compat
from hg_runtime.social_capability.review_schema import SocialReviewItem, SocialReviewStatus

WORKSPACE = Path(__file__).resolve().parents[2]
CLI = WORKSPACE / "scripts" / "dev" / "operator_action_queue.py"


def test_no_approve_all_command_in_cli():
    text = CLI.read_text(encoding="utf-8")
    assert 'add_argument("--approve-all"' not in text
    assert 'add_argument("--batch' not in text
    assert "def cmd_approve_all" not in text


def test_batch_approve_absent_in_cli_help():
    proc = subprocess.run(
        [sys.executable, str(CLI), "--help"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "approve-all" not in proc.stdout.lower()
    assert "batch" not in proc.stdout.lower()


def test_adapter_from_social_review_item():
    sri = SocialReviewItem(
        queue_item_id="sri-test123",
        draft_id="draft-1",
        draft_hash="sha256:abc",
        surface_id="moltbook",
        created_at="2026-06-15T04:00:00+00:00",
        source_task_ref="task-1",
        sanitized_preview="Hello world",
        status=SocialReviewStatus.QUEUED,
    )
    item = from_social_review_item(sri)
    assert item.queue_item_id == "sri-test123"
    assert item.action_type == "social_post"
    compat = to_social_review_compat(item)
    assert compat["permission_granted"] is False
    assert compat["draft_id"] == "draft-1"


def test_hidden_chain_of_thought_absent(tmp_path):
    from tests.operator_action_queue.conftest import make_runtime, sample_request

    q = make_runtime(tmp_path)
    item = q.enqueue(
        sample_request(
            human_summary="Normal task",
            sanitized_preview="No hidden_reasoning here",
        )
    )
    assert "hidden_reasoning" not in item.human_summary
