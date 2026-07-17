"""Phase 17 no live external writes."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]

FORBIDDEN = [
    "hg_runtime/external_write_authority/live_publisher.py",
    "hg_runtime/external_write_authority/live_sender.py",
    "hg_runtime/external_write_authority/live_browser.py",
]


def test_no_live_write_modules():
    for rel in FORBIDDEN:
        assert not (WORKSPACE / rel).exists()


def test_no_pass_stubs_in_external_write_authority():
    pkg = WORKSPACE / "hg_runtime/external_write_authority"
    for py in pkg.glob("*.py"):
        lines = py.read_text(encoding="utf-8").splitlines()
        assert not any(line.strip() == "pass" for line in lines), py.name


def test_env_live_writes_disabled():
    from hg_runtime.external_write_authority.schema import load_policy

    policy = load_policy()
    assert policy["live_writes_allowed"] is False
    assert policy["browser_side_effects_allowed"] is False
    assert policy["hardware_actuation_allowed"] is False


def test_no_secrets_in_git_staged():
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


def test_no_hidden_cot_in_candidate_payload():
    from hg_runtime.external_write_authority.action_candidate import create_candidate

    c = create_candidate(
        run_id="cot-check",
        platform="moltbook",
        action_type="publish_post",
        content="visible",
        scope="platform:moltbook:draft-only",
    )
    payload = c.to_payload()
    for key in payload:
        assert "chain_of_thought" not in key
        assert "hidden_reasoning" not in key
