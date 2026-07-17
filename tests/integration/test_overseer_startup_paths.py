"""Integration tests for overseer startup path resolution."""

import sys

from hg_overseer.overseer_core import overseer_main as om


def test_ws_path_uses_workspace_root(monkeypatch, tmp_path):
    monkeypatch.setattr(om, "workspace_root", tmp_path)
    resolved = om.ws_path("memory/overseer/analysis-state.json")
    assert str(resolved).endswith(str(tmp_path / "memory" / "overseer" / "analysis-state.json"))


def test_cron_health_command_uses_sys_executable():
    cmd = om._cron_health_command()
    assert cmd[0] == sys.executable
    assert cmd[1:] == ["-m", "hg_core.wrappers.cron_health_monitor"]
