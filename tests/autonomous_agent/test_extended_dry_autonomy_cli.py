"""Extended dry autonomy CLI tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]


def test_cli_status_read_only(tmp_path, monkeypatch):
    ext = tmp_path / "ext"
    monkeypatch.setenv("HG_EXTENDED_DRY_AUTONOMY_ROOT", str(ext))
    run_id = "cli-status"
    (ext / run_id).mkdir(parents=True)
    (ext / run_id / "config.json").write_text(json.dumps({"stop_file_path": str(ext / run_id / "STOP")}), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(WORKSPACE / "scripts/dev/agent_zero_extended_dry_autonomy.py"), "--run-id", run_id, "--status"],
        cwd=str(WORKSPACE),
        capture_output=True,
        text=True,
        env={**dict(**{"HG_EXTENDED_DRY_AUTONOMY_ROOT": str(ext)}), **dict(__import__("os").environ)},
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["run_id"] == run_id


def test_cli_pause_local_only(tmp_path, monkeypatch):
    ext = tmp_path / "ext"
    monkeypatch.setenv("HG_EXTENDED_DRY_AUTONOMY_ROOT", str(ext))
    run_id = "cli-pause"
    proc = subprocess.run(
        [sys.executable, str(WORKSPACE / "scripts/dev/agent_zero_extended_dry_autonomy.py"), "--run-id", run_id, "--pause"],
        cwd=str(WORKSPACE),
        capture_output=True,
        text=True,
        env={**dict(__import__("os").environ), "HG_EXTENDED_DRY_AUTONOMY_ROOT": str(ext)},
    )
    assert proc.returncode == 0
    assert (ext / run_id / "PAUSE").is_file()
