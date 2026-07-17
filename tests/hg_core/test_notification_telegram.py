"""Tests for unified Telegram config and send (hg_core.notification_telegram)."""
import os
from pathlib import Path
from unittest.mock import patch


def test_get_telegram_config_prefers_env():
    from hg_core.notification_telegram import get_telegram_config
    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "env-token", "TELEGRAM_CHAT_ID": "999"}):
        cfg = get_telegram_config()
        assert cfg.get("bot_token") == "env-token"
        assert cfg.get("chat_id") == "999"


def test_is_telegram_configured_true_when_token_set():
    from hg_core.notification_telegram import is_telegram_configured
    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "x"}):
        assert is_telegram_configured() is True


def test_is_telegram_configured_false_when_no_token():
    from hg_core.notification_telegram import is_telegram_configured
    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": ""}, clear=False):
        with patch("hg_core.notification_telegram.get_telegram_config", return_value={"chat_id": "1", "bot_token": None}):
            assert is_telegram_configured() is False


def test_send_telegram_returns_error_when_no_token():
    from hg_core.notification_telegram import send_telegram
    with patch("hg_core.notification_telegram.get_telegram_config", return_value={"chat_id": "1", "bot_token": None}):
        result = send_telegram("hello")
        assert result.get("ok") is False
        assert "token" in result.get("error", "").lower()


def test_send_telegram_returns_error_for_empty_message():
    from hg_core.notification_telegram import send_telegram
    result = send_telegram("")
    assert result.get("ok") is False
    assert "empty" in result.get("error", "").lower()
