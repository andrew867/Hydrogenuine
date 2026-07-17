"""Unit tests for short-lived SSE stream tokens (U1.1)."""

import sys
import time
from pathlib import Path

_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_server_path))

from app.services import stream_tokens  # noqa: E402


def test_mint_and_validate_stream_token():
    token = stream_tokens.mint_stream_token("run-abc", ttl_sec=60)
    assert isinstance(token, str)
    assert stream_tokens.validate_stream_token(token, "run-abc") is True
    assert stream_tokens.validate_stream_token(token, "run-other") is False
    assert stream_tokens.validate_stream_token("", "run-abc") is False


def test_stream_token_expires():
    token = stream_tokens.mint_stream_token("run-expire", ttl_sec=0)
    time.sleep(0.01)
    assert stream_tokens.validate_stream_token(token, "run-expire") is False
