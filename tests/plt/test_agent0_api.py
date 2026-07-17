"""PLT Agent #0 API and classifier tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_workspace = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_workspace))
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_server_path))

from hg_plt.classifier import classify_subsystems
from hg_plt.redaction import contains_secret_pattern, redact_payload
from hg_plt.control import execute_control_action
from hg_plt.service import AgentZeroService
from hg_runtime.bus import EventBus
from hg_runtime.demo import build_loop
from hg_runtime.replay import replay


def _headers():
    return {"Authorization": "Bearer test-api-key"}


def _seed_runtime(runtime_dir: Path) -> str:
    loop = build_loop(runtime_dir, require_enabled=False)
    loop.start()
    loop.bus.submit(
        "CHAT_MESSAGE",
        {"session_id": "plt-test", "role": "user", "content": "agent0 gate"},
        source="plt.test",
    )
    loop.run_once(poll_timeout=0.0)
    loop.stop(reason="test")
    return replay(runtime_dir).state_hash


@pytest.fixture
def runtime_env(tmp_path, monkeypatch):
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    state_hash = _seed_runtime(runtime_dir)
    monkeypatch.setenv("HG_PLT_RUNTIME_DIR", str(runtime_dir))
    monkeypatch.setenv("HG_API_KEY", "test-api-key")
    return runtime_dir, state_hash


def test_classifier_labels_scaffold_and_disabled(monkeypatch):
    monkeypatch.delenv("HG_RTC_ENABLED", raising=False)
    items = {s.subsystem: s.status for s in classify_subsystems(replay_ok=True)}
    assert items["HAL"] == "SCAFFOLD"
    assert items["RTC"] == "DISABLED"
    assert items["OEA"] == "STUB"


def test_status_returns_runtime_summary(runtime_env, monkeypatch):
    runtime_dir, state_hash = runtime_env
    monkeypatch.chdir(_workspace)
    svc = AgentZeroService(_workspace)
    status = svc.status()
    assert status["state_hash"] == state_hash
    assert status["event_count"] >= 1
    assert status["replay_health"] == "ok"


def test_events_paginates_and_filters(runtime_env, monkeypatch):
    monkeypatch.chdir(_workspace)
    svc = AgentZeroService(_workspace)
    all_events = svc.events(limit=100)["events"]
    assert all_events
    filtered = svc.events(event_type=all_events[0]["type"], limit=5)["events"]
    assert all_events[0]["type"] == filtered[0]["type"]


def test_world_state_reflects_reducer(runtime_env, monkeypatch):
    monkeypatch.chdir(_workspace)
    ws = AgentZeroService(_workspace).world_state_summary()
    assert ws["state_hash"]
    assert "activity_summary" in ws


def test_scaffold_subsystem_blocks_fake_enable():
    oea = next(s for s in classify_subsystems(replay_ok=True) if s.subsystem == "OEA")
    assert oea.status == "STUB"
    assert oea.blocked


def test_operator_action_requires_target_hash(runtime_env, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    result = execute_control_action(
        "pause",
        workspace=tmp_path,
        target_hash="",
        runtime_dir=runtime_env[0],
    )
    assert result["accepted"] is False
    assert result["refusal_reason"] == "target_hash_required"


def test_operator_action_refuses_hash_mismatch(runtime_env, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    result = execute_control_action(
        "pause",
        workspace=tmp_path,
        target_hash="sha256:deadbeef",
        runtime_dir=runtime_env[0],
    )
    assert result["accepted"] is False
    assert result["refusal_reason"] == "target_hash_mismatch"


def test_pause_and_resume_emit_receipts(runtime_env, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _, state_hash = runtime_env
    pause = execute_control_action(
        "pause",
        workspace=tmp_path,
        target_hash=state_hash,
        runtime_dir=runtime_env[0],
    )
    assert pause["accepted"] is True
    resume = execute_control_action(
        "resume",
        workspace=tmp_path,
        target_hash=state_hash,
        runtime_dir=runtime_env[0],
    )
    assert resume["accepted"] is True


def test_panic_sets_flag_and_receipt(runtime_env, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    runtime_dir, state_hash = runtime_env
    result = execute_control_action(
        "panic",
        workspace=tmp_path,
        target_hash=state_hash,
        runtime_dir=runtime_dir,
        extra={"reason": "test_panic"},
    )
    assert result["accepted"] is True
    assert (runtime_dir / "PANIC").exists()


def test_srp_approval_binds_bundle_hash(runtime_env, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    result = execute_control_action(
        "srp-approve-bundle",
        workspace=tmp_path,
        target_hash="sha256:bundle",
        runtime_dir=runtime_env[0],
        extra={"bundle_hash": "sha256:bundle", "provided_bundle_hash": "sha256:bundle"},
    )
    assert result["accepted"] is False
    assert "signature" in (result["refusal_reason"] or "")


def test_replay_status_not_hardcoded_green(runtime_env, monkeypatch):
    monkeypatch.chdir(_workspace)
    proofs = AgentZeroService(_workspace).proofs()
    assert proofs["replay_ok"] is True
    empty_dir = runtime_env[0].parent / "empty_runtime"
    empty_dir.mkdir()
    monkeypatch.setenv("HG_PLT_RUNTIME_DIR", str(empty_dir))
    empty_proofs = AgentZeroService(_workspace).proofs()
    assert empty_proofs["event_count"] == 0


def test_api_redacts_secrets():
    payload = {"api_key": "super-secret-key", "note": "Bearer abcdefghijklmnop"}
    redacted = redact_payload(payload)
    assert redacted["api_key"] == "[REDACTED]"
    assert "Bearer" not in str(redacted["note"]) or "[REDACTED]" in str(redacted["note"])


def test_no_secret_patterns_in_redacted_output():
    assert contains_secret_pattern("Bearer sk-live-abc123")
    assert not contains_secret_pattern("proposal-only cognition")


@pytest.fixture
def client(monkeypatch, tmp_path):
    if _server_path.exists():
        from fastapi.testclient import TestClient
        from app.core.config import settings
        from app.main import app

        monkeypatch.setattr(settings, "api_key", "test-api-key")
    else:
        pytest.skip("operator_console/server not found")
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    monkeypatch.setenv("HG_API_KEY", "test-api-key")
    return TestClient(app)


def test_http_status_endpoint(client, runtime_env, monkeypatch):
    monkeypatch.chdir(_workspace)
    resp = client.get("/api/v1/agent0/status", headers=_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert body["state_hash"] == runtime_env[1]


def test_http_pause_refuses_bad_hash(client, runtime_env, monkeypatch):
    monkeypatch.chdir(_workspace)
    resp = client.post(
        "/api/v1/agent0/pause",
        headers=_headers(),
        json={"target_hash": "sha256:bad"},
    )
    assert resp.status_code == 403


def test_arousal_shows_restrict_only(client, runtime_env, monkeypatch):
    monkeypatch.chdir(_workspace)
    resp = client.get("/api/v1/agent0/arousal", headers=_headers())
    assert resp.status_code == 200
    assert resp.json()["restrict_only"] is True
