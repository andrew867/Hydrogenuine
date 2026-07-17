"""Product API demo defaults: live vs shadow action mode."""

import sys
from pathlib import Path

_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_server_path))


def test_default_action_mode_live_when_enabled():
    from app.api.product_v1 import _default_action_mode

    assert _default_action_mode({"demo_mode": True, "live_actions_enabled": True}) == "live"


def test_default_action_mode_shadow_when_disabled():
    from app.api.product_v1 import _default_action_mode

    assert _default_action_mode({"demo_mode": True, "live_actions_enabled": False}) == "shadow"
