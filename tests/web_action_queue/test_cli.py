"""CLI tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

CLI = Path(__file__).resolve().parents[2] / "scripts" / "dev" / "web_action_queue.py"
WORKSPACE = Path(__file__).resolve().parents[2]


def test_cli_no_execute_option():
    text = CLI.read_text(encoding="utf-8")
    assert 'add_argument("--execute"' not in text
    assert "def cmd_execute" not in text


def test_cli_help_no_execute():
    proc = subprocess.run(
        [sys.executable, str(CLI), "--help"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "--execute" not in proc.stdout


def test_cli_form_submit_shows_denied(tmp_path, monkeypatch):
    import hg_runtime.web_action_queue.queue as wq

    monkeypatch.setattr(wq, "WORKSPACE", tmp_path)
    proc = subprocess.run(
        [sys.executable, str(CLI), "--enqueue-form-submit", "https://example.com/form"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "DENIED" in proc.stdout or "denied" in proc.stdout.lower()
