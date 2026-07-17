"""Phase 18 no unscoped live actions."""
from __future__ import annotations

import subprocess
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]

FORBIDDEN = [
    "hg_runtime/external_write_authority/live_publisher.py",
    "hg_runtime/external_write_authority/live_browser.py",
]


def test_no_broad_live_modules():
    for rel in FORBIDDEN:
        assert not (WORKSPACE / rel).exists()


def test_no_pass_stubs_in_phase18_modules():
    names = ("live_smoke.py", "live_permit.py", "platform_proof.py", "incident_plan.py")
    for name in names:
        py = WORKSPACE / "hg_runtime/external_write_authority" / name
        lines = py.read_text(encoding="utf-8").splitlines()
        assert not any(line.strip() == "pass" for line in lines), name


def test_review_not_approval():
    from hg_runtime.external_write_authority.live_smoke import load_phase18_policy

    assert load_phase18_policy()["review_queue_is_approval"] is False


def test_model_output_not_permission():
    from hg_runtime.external_write_authority.broker_integration import create_candidate_from_broker_admission
    import pytest

    with pytest.raises(PermissionError):
        create_candidate_from_broker_admission(
            run_id="model",
            platform="moltbook",
            action_type="publish_post",
            content="x",
            scope="s",
            capability_decision_ref="model_output:go",
        )


def test_no_mass_messaging_path():
    from hg_runtime.external_write_authority.live_smoke import load_phase18_policy

    assert load_phase18_policy()["mass_messaging_allowed"] is False


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
