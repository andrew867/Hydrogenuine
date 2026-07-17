"""Phase 19 no unscoped live actions."""
from __future__ import annotations

import subprocess
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]


def test_no_pass_stubs():
    names = (
        "incident_audit.py",
        "platform_reverify.py",
        "rollback.py",
        "incident_report.py",
        "action_ledger.py",
        "phase19_snapshot.py",
    )
    for name in names:
        py = WORKSPACE / "hg_runtime/external_write_authority" / name
        lines = py.read_text(encoding="utf-8").splitlines()
        assert not any(line.strip() == "pass" for line in lines), name


def test_policy_blocks_browser_hardware():
    import json

    pol = json.loads(
        (WORKSPACE / "configs/agent_zero/phase19_external_action_audit_policy.json").read_text(encoding="utf-8")
    )
    assert pol["browser_side_effects_allowed"] is False
    assert pol["hardware_actuation_allowed"] is False


def test_broker_refuses_publish():
    from hg_runtime.capability_broker.action_registry import is_forbidden_action

    assert is_forbidden_action("publish")
    assert is_forbidden_action("send")
    assert is_forbidden_action("reply_live")


def test_no_secrets_staged():
    proc = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return
    for line in proc.stdout.splitlines():
        low = line.lower()
        assert ".env" not in low
        assert ".hg-local" not in low
