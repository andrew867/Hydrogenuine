"""Tests for CLI flag hardening and proof flag doctor."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from agent_zero_cli_flag_doctor import check_proof_command, FLAG_REGISTRY


def test_wired_flag_allowed():
    result = check_proof_command(["--question", "test", "--model-selection", "dynamic"])
    assert result["clean"] is True
    assert len(result["violations"]) == 0


def test_future_only_rejected():
    result = check_proof_command(["--ensemble-mode", "multi_model_local"])
    assert result["clean"] is False
    assert any(v["flag"] == "--ensemble-mode" for v in result["violations"])


def test_removed_flag_rejected():
    result = check_proof_command(["--some-nonexistent-flag"])
    assert result["clean"] is False
    assert any(v["reason"] == "unknown_flag" for v in result["violations"])


def test_proof_command_doctor_catches_noop():
    result = check_proof_command([
        "--question", "test",
        "--model-selection", "dynamic",
        "--allow-any-local-model",
        "--max-distinct-models", "5",
    ])
    assert result["clean"] is False
    violations = {v["flag"] for v in result["violations"]}
    assert "--allow-any-local-model" in violations
    assert "--max-distinct-models" in violations


def test_clean_proof_command():
    cmd = [
        "--question", "test",
        "--model-selection", "dynamic",
        "--resource-risk-ceiling", "medium",
        "--enable-backlog-drain",
        "--backlog-file", "test.jsonl",
        "--max-backlog-topics", "8",
        "--enable-source-screenshots",
        "--min-wall-clock-seconds", "900",
        "--continue-until-min-duration",
    ]
    result = check_proof_command(cmd)
    assert result["clean"] is True


def test_discovery_timeout_is_wired():
    entry = next(f for f in FLAG_REGISTRY if f["flag"] == "--discovery-timeout")
    assert entry["status"] == "wired"
    assert entry["allowed_in_proof"] is True


def test_all_future_flags_not_allowed_in_proof():
    future = [f for f in FLAG_REGISTRY if f["status"] == "future_only"]
    for f in future:
        assert f["allowed_in_proof"] is False, f"{f['flag']} is future_only but allowed_in_proof"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
