"""
Tests for Agentchan JWT resolution: module-based credentials path, load_jwt behavior, error message.
"""
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest


def test_load_jwt_returns_token_when_creds_file_has_agentchan_jwt(tmp_path):
    """When find_credentials_file returns a path and file contains agentchan_jwt, load_jwt returns it."""
    creds_file = tmp_path / "credentials.json"
    creds_file.write_text(json.dumps({"agentchan_jwt": "test-token-123"}, ensure_ascii=False), encoding="utf-8")

    with patch("agentchan.agentchan_api_client_async.find_credentials_file", return_value=creds_file):
        from agentchan.agentchan_api_client_async import load_jwt
        with patch.dict(os.environ, {}, clear=False):
            for key in ("AGENTCHAN_JWT", "AGENTCHAN_TOKEN"):
                os.environ.pop(key, None)
        result = load_jwt()
    assert result == "test-token-123"


def test_load_jwt_returns_none_when_creds_file_not_found_and_env_unset():
    """When find_credentials_file returns None and env vars are unset, load_jwt returns None."""
    with patch("agentchan.agentchan_api_client_async.find_credentials_file", return_value=None):
        from agentchan.agentchan_api_client_async import load_jwt
        with patch.dict(os.environ, {}, clear=False):
            for key in ("AGENTCHAN_JWT", "AGENTCHAN_TOKEN"):
                os.environ.pop(key, None)
        result = load_jwt()
    assert result is None


def test_load_jwt_raises_on_unexpected_exception(tmp_path):
    """When credentials file exists but reading causes an unexpected error, load_jwt re-raises."""
    creds_file = tmp_path / "credentials.json"
    creds_file.write_text(json.dumps({"agentchan_jwt": "x"}, ensure_ascii=False), encoding="utf-8")

    from agentchan.agentchan_api_client_async import load_jwt
    with patch("agentchan.agentchan_api_client_async.find_credentials_file", return_value=creds_file), \
         patch("builtins.open", side_effect=RuntimeError("simulated read error")):
        with patch.dict(os.environ, {}, clear=False):
            for key in ("AGENTCHAN_JWT", "AGENTCHAN_TOKEN"):
                os.environ.pop(key, None)
        with pytest.raises(RuntimeError, match="simulated read error"):
            load_jwt()


def test_client_value_error_includes_what_was_tried():
    """When JWT not found, ValueError message includes env and credentials file hint."""
    from agentchan.agentchan_api_client_async import AgentchanAsyncClient
    with patch("agentchan.agentchan_api_client_async.load_jwt", return_value=None), \
         patch("agentchan.agentchan_api_client_async.find_credentials_file", return_value=None):
        with pytest.raises(ValueError) as exc_info:
            AgentchanAsyncClient()
    msg = str(exc_info.value)
    assert "AGENTCHAN_JWT" in msg or "credentials" in msg
    assert "not found" in msg or "unset" in msg


def test_load_jwt_uses_task_keystore_for_bayman(monkeypatch):
    from agentchan.agentchan_api_client_async import load_jwt

    monkeypatch.setattr(
        "agentchan.agentchan_api_client_async.resolve_task_platform_credential",
        lambda **kwargs: "bayman-jwt",
    )
    token = load_jwt(task_name="newfoundland-bayman-agentchan-engage")
    assert token == "bayman-jwt"


def test_client_value_error_mentions_keystore_for_bayman():
    from agentchan.agentchan_api_client_async import AgentchanAsyncClient

    with patch("agentchan.agentchan_api_client_async.load_jwt", return_value=None):
        with pytest.raises(ValueError) as exc_info:
            AgentchanAsyncClient(task_name="newfoundland-bayman-agentchan-engage")
    assert "keystore-backed social account assignment" in str(exc_info.value)


def test_setup_account_registration_proof_can_be_persisted(monkeypatch, tmp_path):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    from agentchan.setup_agentchan import _persist_registration_proof
    from hg_gateway.db import get_connection

    artifact = _persist_registration_proof(
        social_account_id="acct-agentchan",
        tenant_id="tenant-a",
        account_name="bayman-agentchan",
        result={"ok": True, "boards": ["all"]},
    )
    assert artifact is not None
    assert artifact["artifact_type"] == "registration_proof"
    with get_connection(str(tmp_path / "gateway.sqlite3")) as conn:
        row = conn.execute(
            "SELECT artifact_type, related_id FROM proof_artifacts WHERE related_kind = 'social_account'"
        ).fetchone()
    assert row is not None
    assert row[0] == "registration_proof"
    assert row[1] == "acct-agentchan"
