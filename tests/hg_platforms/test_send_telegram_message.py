from hg_platforms.moltbook.send_telegram_message import _sanitize_heartbeat_message


def test_sanitize_heartbeat_message_strips_thinking_blocks():
    message = "<think>internal</think>\nActual reply"
    assert _sanitize_heartbeat_message(message) == "Actual reply"


def test_sanitize_heartbeat_message_handles_malformed_backslash_think_blocks():
    message = "<\\think>internal</\\think>\nActual reply"
    assert _sanitize_heartbeat_message(message) == "Actual reply"
