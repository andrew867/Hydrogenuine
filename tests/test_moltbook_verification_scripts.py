import json
import subprocess
import sys
from pathlib import Path


workspace_root = Path(__file__).parent.parent


def test_verify_post_help_mentions_proof_flags():
    script_path = workspace_root / "hg_platforms" / "moltbook" / "verify_moltbook_post.py"
    result = subprocess.run(
        [sys.executable, str(script_path), "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--social-account-id" in result.stdout
    assert "--task-name" in result.stdout


def test_verify_comment_help_mentions_proof_flags():
    script_path = workspace_root / "hg_platforms" / "moltbook" / "verify_moltbook_comment.py"
    result = subprocess.run(
        [sys.executable, str(script_path), "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--social-account-id" in result.stdout
    assert "--task-name" in result.stdout


def test_verify_post_persist_verification_proof_writes_account_artifact(monkeypatch, tmp_path):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    from hg_platforms.moltbook.verify_moltbook_post import _persist_verification_proof
    from hg_gateway.db import get_connection

    artifact = _persist_verification_proof(
        social_account_id="acct-moltbook",
        tenant_id="tenant-a",
        task_name="newfoundland-bayman-moltbook-auto-post",
        post_id="post-1",
        post_url="https://moltbook.example/post-1",
        result={"success": True},
    )
    assert artifact is not None
    assert artifact["artifact_type"] == "verification_proof"
    with get_connection(str(tmp_path / "gateway.sqlite3")) as conn:
        row = conn.execute(
            "SELECT artifact_type, related_id FROM proof_artifacts WHERE related_kind = 'social_account'"
        ).fetchone()
    assert row is not None
    assert row[0] == "verification_proof"
    assert row[1] == "acct-moltbook"


def test_verify_comment_persist_verification_proof_writes_account_artifact(monkeypatch, tmp_path):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    from hg_platforms.moltbook.verify_moltbook_comment import _persist_verification_proof
    from hg_gateway.db import get_connection

    artifact = _persist_verification_proof(
        social_account_id="acct-moltbook",
        tenant_id="tenant-a",
        task_name="newfoundland-bayman-moltbook-engage",
        post_id="post-1",
        comment_id="comment-1",
        result={"success": True},
    )
    assert artifact is not None
    assert artifact["artifact_type"] == "verification_proof"
    payload = json.loads(Path(artifact["path"]).read_text(encoding="utf-8"))
    assert payload["task_name"] == "newfoundland-bayman-moltbook-engage"
    assert payload["operational_agent_id"] == "newfoundland-bayman"
    with get_connection(str(tmp_path / "gateway.sqlite3")) as conn:
        row = conn.execute(
            "SELECT artifact_type, related_id FROM proof_artifacts WHERE related_kind = 'social_account'"
        ).fetchone()
    assert row is not None
    assert row[0] == "verification_proof"
    assert row[1] == "acct-moltbook"
