"""CT proof command_log.jsonl conformance tests."""

from __future__ import annotations

import json
from pathlib import Path

from hg_core.proof.command_log import record_command, validate_command_log, validate_ct_gate_scripts

WORKSPACE = Path(__file__).resolve().parents[2]


def test_record_and_validate_command_log(tmp_path: Path) -> None:
    log_path = tmp_path / "command_log.jsonl"
    record_command(
        log_path,
        argv=["pytest", "tests/example", "-q"],
        cwd=WORKSPACE,
        exit_code=0,
        duration_s=1.23,
        stdout="ok",
        stderr="",
    )
    ok, findings = validate_command_log(log_path)
    assert ok, findings
    entry = json.loads(log_path.read_text().strip())
    assert entry["argv"] == ["pytest", "tests/example", "-q"]
    assert entry["exit_code"] == 0


def test_missing_command_log_fails(tmp_path: Path) -> None:
    ok, findings = validate_command_log(tmp_path / "missing.jsonl")
    assert not ok
    assert findings[0].check == "missing"


def test_ct_gate_scripts_declare_command_log() -> None:
    result = validate_ct_gate_scripts(WORKSPACE)
    assert result["ok"], result.get("missing", [])


def test_secrets_rejected_in_command_log(tmp_path: Path) -> None:
    log_path = tmp_path / "command_log.jsonl"
    log_path.write_text(
        json.dumps(
            {
                "argv": ["echo", "sk-abcdefghijklmnopqrstuvwxyz"],
                "cwd": str(WORKSPACE),
                "exit_code": 0,
                "duration_s": 0.1,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    ok, findings = validate_command_log(log_path)
    assert not ok
    assert any(f.check == "secret_leak" for f in findings)
