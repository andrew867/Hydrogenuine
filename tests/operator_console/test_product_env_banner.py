"""Product /env banner exposes live vs shadow for UI."""

import sys
from pathlib import Path

_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_server_path))


def test_env_banner_includes_action_mode_live(monkeypatch):
    monkeypatch.setenv("HG_DEMO_LIVE_ACTIONS_ENABLED", "1")
    monkeypatch.setenv("HG_DEMO_MODE", "1")
    from app.api.product_v1 import env_banner

    data = env_banner()
    assert data.get("action_mode") == "live"
    assert data.get("live_actions_enabled") is True
