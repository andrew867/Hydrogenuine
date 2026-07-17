"""Demo-mode service tests: config, fake destination, and seed generator."""

import json
import os
import sys
import tempfile
from pathlib import Path

_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_server_path))


def test_demo_mode_live_actions_disabled_by_default(monkeypatch):
    """When demo mode is enabled without overrides, live actions default to disabled."""
    from app.services import demo_config as demo_config_mod

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        monkeypatch.setenv("HG_WORKSPACE", str(root))
        monkeypatch.delenv("HG_DEMO_LIVE_ACTIONS_ENABLED", raising=False)
        monkeypatch.setenv("HG_DEMO_MODE", "true")
        config = demo_config_mod.get_demo_config()
        assert config.get("demo_mode") is True
        assert config.get("live_actions_enabled") is False


def test_demo_live_actions_env_override(monkeypatch):
    """HG_DEMO_LIVE_ACTIONS_ENABLED enables live actions when no file override."""
    from app.services import demo_config as demo_config_mod

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        monkeypatch.setenv("HG_WORKSPACE", str(root))
        monkeypatch.setenv("HG_DEMO_MODE", "true")
        monkeypatch.setenv("HG_DEMO_LIVE_ACTIONS_ENABLED", "1")
        config = demo_config_mod.get_demo_config()
        assert config.get("live_actions_enabled") is True


def test_fake_destination_records_would_act():
    """Fake destination records would-act events and redacts sensitive keys."""
    from app.services.fake_destination import FakeDestinationLogger

    log_path = Path(tempfile.mkdtemp()) / "would_act.jsonl"
    try:
        logger = FakeDestinationLogger(log_path)
        logger.log_would_act(
            workflow_id="workflow-a",
            run_id="run-1",
            action="post",
            payload={"secret": "x", "nested": {"token": "t", "ok": "value"}, "list": [{"password": "p"}, {"safe": 1}]},
        )
        with open(log_path, encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry.get("event") == "would_act"
        payload = entry.get("payload") or {}
        assert "secret" not in payload
        assert payload.get("nested", {}).get("ok") == "value"
        assert "token" not in payload.get("nested", {})
        assert payload.get("list", [{}])[0].get("password") is None
    finally:
        os.unlink(log_path)


def test_seed_loader_output_shape():
    """Seed loader produces deterministic workflow/run/approval/deadletter/metrics structures."""
    from app.services.seed_loader import load_seed_profile, generate_seed_data

    profile = {"profile_name": "small", "workflows": ["w1"], "run_history": {"days": 1, "avg_runs_per_day_per_workflow": 2}}
    data = generate_seed_data(profile, output_dir=Path(tempfile.mkdtemp()), rng_seed=123)
    assert "workflows" in data
    assert isinstance(data.get("workflows", []), list)
    assert isinstance(data.get("runs", []), list)
    assert isinstance(data.get("approvals", []), list)
    assert isinstance(data.get("deadletters", []), list)
    assert isinstance(data.get("metrics", {}), dict)
    profile_from_name = load_seed_profile("small")
    assert isinstance(profile_from_name.get("workflows"), list)
