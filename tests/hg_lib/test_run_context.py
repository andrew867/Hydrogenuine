"""Tests for hg_lib.run_context."""

from pathlib import Path

from hg_lib.run_context import RunContext


def test_run_context_create():
    """RunContext.create produces valid context."""
    root = Path("/tmp/ws")
    ctx = RunContext.create(root, job_id="test-job", platform="moltbook", mode="engage")
    assert ctx.workspace_root == root
    assert ctx.job_id == "test-job"
    assert ctx.platform == "moltbook"
    assert ctx.mode == "engage"
    assert len(ctx.run_id) == 36  # uuid4 format
    assert ctx.start_time is not None
