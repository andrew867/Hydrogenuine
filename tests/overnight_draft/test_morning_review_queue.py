"""Morning review queue tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))


@pytest.fixture
def run_dir(tmp_path: Path) -> Path:
    rd = tmp_path / "soak_run"
    rd.mkdir()
    draft = {
        "draft_id": "odraft-test001",
        "draft_type": "post",
        "draft_text": "Hello morning review",
        "draft_text_hash": "abc123",
        "risk_class": "low",
        "status": "queued_for_morning_review",
        "sanitized_prompt_preview": "Hello…",
        "source_context_ref": "curated:test",
        "source_surface": "moltbook",
        "target_surface": "moltbook",
        "authority_created": False,
        "permission_granted": False,
        "publish_attempted": False,
        "sent": False,
        "receipt_ref": "odrec-test",
    }
    (rd / "draft_queue.jsonl").write_text(json.dumps(draft) + "\n", encoding="utf-8")
    (rd / "receipts.jsonl").touch()
    return rd


def _cli(*args: str) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "scripts/dev/agent_zero_morning_review_queue.py", *args]
    return subprocess.run(cmd, cwd=WORKSPACE, capture_output=True, text=True)


def test_list_works(run_dir: Path):
    r = _cli("--run-dir", str(run_dir), "--list")
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["count"] == 1
    assert "Hello morning review" in payload["items"][0]["preview"]
    assert payload["items"][0]["preview"] != payload["items"][0].get("sanitized_prompt_preview")


def test_list_preview_uses_draft_text_not_reason(tmp_path: Path):
    rd = tmp_path / "preview_run"
    rd.mkdir()
    draft = {
        "draft_id": "odraft-reason-trap",
        "draft_type": "comment",
        "draft_text": "Actual body text about bounded soak receipts for operator review.",
        "draft_text_hash": "hash-body",
        "risk_class": "low",
        "status": "queued_for_morning_review",
        "sanitized_prompt_preview": "Overnight comment draft from local thread context",
        "reason_for_draft": "Overnight comment draft from local thread context",
        "source_surface": "moltbook",
        "target_surface": "moltbook",
    }
    (rd / "draft_queue.jsonl").write_text(json.dumps(draft) + "\n", encoding="utf-8")
    (rd / "receipts.jsonl").touch()
    r = _cli("--run-dir", str(rd), "--list")
    assert r.returncode == 0
    item = json.loads(r.stdout)["items"][0]
    assert "Actual body text" in item["preview"]
    assert "Overnight comment draft" not in item["preview"]
    assert item["source_surface"] == "moltbook"


def test_missing_draft_text_is_red(tmp_path: Path):
    rd = tmp_path / "missing_body"
    rd.mkdir()
    draft = {
        "draft_id": "odraft-nobody",
        "draft_type": "reply",
        "draft_text_hash": "hash-x",
        "risk_class": "low",
        "status": "queued_for_morning_review",
        "sanitized_prompt_preview": "Overnight reply draft from message center fixture",
        "reason_for_draft": "Overnight reply draft from message center fixture",
    }
    (rd / "draft_queue.jsonl").write_text(json.dumps(draft) + "\n", encoding="utf-8")
    (rd / "receipts.jsonl").touch()
    r = _cli("--run-dir", str(rd), "--list", "--show-quality")
    assert r.returncode == 0
    item = json.loads(r.stdout)["items"][0]
    assert item["preview"] == "RED_MISSING_DRAFT_TEXT"
    assert item["output_quality"] == "RED_MISSING_DRAFT_TEXT"


def test_list_flags_fixture_rehearsal(tmp_path: Path):
    rd = tmp_path / "fixture_flag"
    rd.mkdir()
    draft = {
        "draft_id": "odraft-fix",
        "draft_type": "comment",
        "draft_text": "[DRAFT COMMENT — NOT POSTED] Thoughtful question about bounded soak receipts.",
        "draft_text_hash": "h1",
        "risk_class": "low",
        "status": "queued_for_morning_review",
    }
    (rd / "draft_queue.jsonl").write_text(json.dumps(draft) + "\n", encoding="utf-8")
    (rd / "receipts.jsonl").touch()
    r = _cli("--run-dir", str(rd), "--list", "--show-quality")
    item = json.loads(r.stdout)["items"][0]
    assert item["fixture_rehearsal"] is True
    assert item["output_quality"] == "RED_FIXTURE_CORPUS"


def test_show_works(run_dir: Path):
    r = _cli("--run-dir", str(run_dir), "--show", "odraft-test001")
    assert r.returncode == 0
    assert json.loads(r.stdout)["draft_id"] == "odraft-test001"


def test_approve_locks_hash(run_dir: Path):
    r = _cli("--run-dir", str(run_dir), "--approve", "odraft-test001", "--operator-ref", "test-op")
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["ok"]
    assert payload["approval"]["approved_hash"] == "abc123"
    assert payload["published"] is False


def test_edit_invalidates_prior_approval(run_dir: Path, tmp_path: Path):
    _cli("--run-dir", str(run_dir), "--approve", "odraft-test001", "--operator-ref", "test-op")
    text = tmp_path / "edited.txt"
    text.write_text("Edited body", encoding="utf-8")
    r = _cli("--run-dir", str(run_dir), "--edit", "odraft-test001", "--text-file", str(text), "--operator-ref", "test-op")
    assert r.returncode == 0
    state = json.loads((run_dir / "morning_review_state.json").read_text(encoding="utf-8"))
    assert "odraft-test001" not in state.get("approvals", {})


def test_deny_marks_denied(run_dir: Path):
    r = _cli("--run-dir", str(run_dir), "--deny", "odraft-test001", "--operator-ref", "test-op")
    assert r.returncode == 0
    state = json.loads((run_dir / "morning_review_state.json").read_text(encoding="utf-8"))
    assert "odraft-test001" in state["denials"]


def test_approve_does_not_publish(run_dir: Path):
    r = _cli("--run-dir", str(run_dir), "--approve", "odraft-test001", "--operator-ref", "test-op")
    payload = json.loads(r.stdout)
    assert payload["published"] is False


def test_publish_approved_refuses(run_dir: Path):
    _cli("--run-dir", str(run_dir), "--approve", "odraft-test001", "--operator-ref", "test-op")
    r = _cli("--run-dir", str(run_dir), "--publish-approved", "odraft-test001", "--operator-ref", "test-op")
    assert r.returncode != 0
    assert json.loads(r.stdout)["published"] is False


def test_no_approve_all_in_cli():
    text = (WORKSPACE / "scripts/dev/agent_zero_morning_review_queue.py").read_text(encoding="utf-8")
    assert "--approve-all" not in text
    assert "approve_all" not in text
