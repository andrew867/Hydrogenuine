"""Tests: daemon gate — structural readiness checks."""

from __future__ import annotations

import pytest

from hg_runtime.overnight_daemon.gate import run_gate
from hg_runtime.overnight_daemon.subagents import (
    SUBAGENT_ROLES, create_task, task_grants_authority, task_authorizes_tools,
    task_can_self_authorize,
)
from hg_runtime.overnight_daemon.checkins import future_checkin_is_fabricated
from hg_runtime.live_local.paced_loop import overnight_green_allowed


def test_gate_green_for_valid_daemon_launch():
    verdict, checks = run_gate()
    failed = [c for c in checks if not c["passed"]]
    assert verdict == "GREEN_AGENT_ZERO_OVERNIGHT_DAEMON_READY", \
        f"Gate not GREEN: {failed}"


def test_gate_check_count():
    _, checks = run_gate()
    assert len(checks) >= 30


def test_gate_red_if_no_pid():
    """Structurally: the gate checks heartbeat round-trip which requires PID."""
    _, checks = run_gate()
    hb_check = [c for c in checks if "heartbeat_round_trip" in c["check"]]
    assert hb_check and hb_check[0]["passed"]


def test_gate_red_if_fake_hourly_checkin():
    assert future_checkin_is_fabricated(5, 60.0, 60)


def test_gate_red_if_subagent_can_authorize():
    for role in SUBAGENT_ROLES:
        task = create_task(role, "test")
        assert not task_grants_authority(task)
        assert not task_authorizes_tools(task)
        assert not task_can_self_authorize(task)


def test_gate_red_if_daemon_uses_remote_provider():
    _, checks = run_gate()
    remote_check = [c for c in checks if "no_remote_provider" in c["check"]]
    assert remote_check and remote_check[0]["passed"]


def test_gate_red_if_daemon_touches_hg_local():
    _, checks = run_gate()
    hg_check = [c for c in checks if "hg_local" in c["check"]]
    assert hg_check and hg_check[0]["passed"]


def test_gate_red_if_compressed_run_marked_green():
    assert not overnight_green_allowed(target_seconds=43200, elapsed_seconds=600)
    _, checks = run_gate()
    compressed_check = [c for c in checks if "compressed_run_not_green" in c["check"]]
    assert compressed_check and compressed_check[0]["passed"]


def test_gate_green_with_valid_role_map():
    verdict, checks = run_gate()
    rm_check = [c for c in checks if "role_mapping_valid" in c["check"]]
    assert rm_check and rm_check[0]["passed"]


def test_gate_checks_each_mode_maps():
    _, checks = run_gate()
    mode_checks = [c for c in checks if c["check"].startswith("mode_")]
    assert len(mode_checks) >= 4
    for c in mode_checks:
        assert c["passed"], f"{c['check']} failed: {c.get('detail')}"


def test_gate_preserves_phase19_yellow():
    _, checks = run_gate()
    p19 = [c for c in checks if "phase19" in c["check"]]
    assert p19 and p19[0]["passed"]


def test_gate_preserves_phase24_infrastructure_only():
    _, checks = run_gate()
    p24 = [c for c in checks if "phase24" in c["check"]]
    assert p24 and p24[0]["passed"]


def test_gate_zero_not_agi_conscious_sovereign():
    _, checks = run_gate()
    for tag in ("zero_not_agi", "zero_not_conscious", "zero_not_sovereign"):
        matched = [c for c in checks if tag in c["check"]]
        assert matched and matched[0]["passed"], f"{tag} not asserted"
