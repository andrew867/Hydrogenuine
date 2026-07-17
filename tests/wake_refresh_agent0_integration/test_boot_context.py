"""Agent Zero WRR boot integration tests."""

from __future__ import annotations

from hg_runtime.wake_refresh.agent0_context import WAKE_REFRESH_BOOT_INSTRUCTION, build_wake_refresh_boot_context
from hg_runtime.wake_refresh.refresh_cycle import WakeRefreshConfig, run_wake_refresh_cycle


def test_boot_context_fields(tmp_path):
    cycle = run_wake_refresh_cycle(workspace=tmp_path, config=WakeRefreshConfig(dry_run=True))
    ctx = build_wake_refresh_boot_context(cycle)
    assert ctx["enabled"] is True
    assert ctx["permission_granted"] is False
    assert ctx["authority_created"] is False
    assert "wake_readiness" in ctx


def test_cannot_grant_permission():
    assert "not authorize" in WAKE_REFRESH_BOOT_INSTRUCTION.lower()
