from __future__ import annotations

from pathlib import Path

import pytest

from hg_dep.appliance_config import ApplianceConfig, ApplianceConfigError, load_appliance_config


def test_load_appliance_config_from_env_file(tmp_path: Path):
    env_file = tmp_path / "appliance.env"
    env_file.write_text(
        "\n".join(
            [
                "HG_APPLIANCE_RUNTIME_DIR=memory/appliance-test",
                "HG_APPLIANCE_LOG_DIR=memory/appliance-test/logs",
                "HG_APPLIANCE_COGNITION_MODE=stub",
                "HG_APPLIANCE_MAX_TICKS=3",
                "HG_RTC_ENABLED=0",
            ]
        ),
        encoding="utf-8",
    )
    config = load_appliance_config(env_file=env_file, overrides={"HG_RTC_ENABLED": "0"})
    assert config.runtime_dir == Path("memory/appliance-test")
    assert config.log_dir == Path("memory/appliance-test/logs")
    assert config.cognition_mode == "stub"
    assert config.max_ticks == 3
    assert config.daemon_mode is False


def test_vllm_mode_requires_base_url():
    with pytest.raises(ApplianceConfigError, match="vllm_base_url"):
        ApplianceConfig(
            runtime_dir=Path("memory/runtime"),
            log_dir=Path("memory/runtime/logs"),
            cognition_mode="vllm",
        )


def test_daemon_and_max_ticks_conflict():
    with pytest.raises(ApplianceConfigError, match="not both"):
        ApplianceConfig(
            runtime_dir=Path("memory/runtime"),
            log_dir=Path("memory/runtime/logs"),
            max_ticks=5,
            daemon_mode=True,
        )


def test_apply_cognition_env_stub(monkeypatch):
    monkeypatch.delenv("HG_RTC_COGNITION_LIVE", raising=False)
    config = ApplianceConfig(
        runtime_dir=Path("memory/runtime"),
        log_dir=Path("memory/runtime/logs"),
        cognition_mode="stub",
    )
    config.apply_cognition_env()
    import os

    assert os.environ["HG_RTC_COGNITION_PROVIDER"] == "fake"
    assert os.environ["HG_RTC_COGNITION_STREAMING"] == "1"
    assert "HG_RTC_COGNITION_LIVE" not in os.environ


def test_apply_cognition_env_vllm_offline_by_default(monkeypatch):
    config = ApplianceConfig(
        runtime_dir=Path("memory/runtime"),
        log_dir=Path("memory/runtime/logs"),
        cognition_mode="vllm",
        vllm_base_url="http://127.0.0.1:8000/v1",
        cognition_live=False,
    )
    config.apply_cognition_env()
    import os

    assert os.environ["HG_RTC_COGNITION_PROVIDER"] == "vllm"
    assert os.environ["HG_RTC_COGNITION_BASE_URL"] == "http://127.0.0.1:8000/v1"
    assert os.environ.get("HG_RTC_COGNITION_LIVE") != "1"
