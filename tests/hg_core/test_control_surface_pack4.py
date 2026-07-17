"""
Control Surface Pack 4: Operational hardening — rate limits, fail-closed auth, chaos drills, SLOs, stream hardening.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hg_core.control_surface.rate_limit import (
    check_rate_limit,
    is_dangerous_control,
    require_step_up_auth,
)
from hg_core.control_surface.stream_hardening import (
    HEARTBEAT_INTERVAL_SECONDS,
    suggest_polling,
    should_drop_for_backpressure,
    resume_from,
    BACKPRESSURE_PRIORITY_SAFETY_CRITICAL,
    BACKPRESSURE_PRIORITY_LOW,
)
from hg_core.control_surface.chaos_drills import (
    kill_stream,
    lag_materializers,
    revoke_bridge_trust_root,
)
from hg_core.observability.slo import load_slo_config, check_slos
from hg_core.observability.metrics import (
    get_metrics,
    record_stream_connection,
    record_stream_dropped,
    record_api_request,
    record_control_action,
)


def test_rate_limit_enforced() -> None:
    """Rate limit denies when over requests_per_minute within window."""
    key = "test_actor_1"
    # Allow first 2
    assert check_rate_limit(key, requests_per_minute=2, window_seconds=60) is True
    assert check_rate_limit(key, requests_per_minute=2, window_seconds=60) is True
    # Third denied
    assert check_rate_limit(key, requests_per_minute=2, window_seconds=60) is False


def test_rate_limit_different_keys() -> None:
    """Different keys have independent limits."""
    assert check_rate_limit("user_a", requests_per_minute=1, window_seconds=60) is True
    assert check_rate_limit("user_b", requests_per_minute=1, window_seconds=60) is True
    assert check_rate_limit("user_a", requests_per_minute=1, window_seconds=60) is False
    assert check_rate_limit("user_b", requests_per_minute=1, window_seconds=60) is False


def test_is_dangerous_control() -> None:
    """Override and handoff are dangerous; list is not."""
    assert is_dangerous_control("control/override") is True
    assert is_dangerous_control("control/handoff") is True
    assert is_dangerous_control("control/pause") is True
    assert is_dangerous_control("entities") is False


def test_require_step_up_auth_deny_by_default() -> None:
    """Without step-up, dangerous action is denied for default actor."""
    actor = {"agent_id": "ops", "key_id": "default"}
    assert require_step_up_auth(actor, "control/override") is False


def test_require_step_up_auth_with_key_id() -> None:
    """Non-default key_id satisfies step-up (stub)."""
    actor = {"agent_id": "ops", "key_id": "quorum-1"}
    assert require_step_up_auth(actor, "control/override") is True


def test_suggest_polling() -> None:
    """After N failures suggest polling."""
    assert suggest_polling(0) is False
    assert suggest_polling(2) is False
    assert suggest_polling(3) is True
    assert suggest_polling(5) is True


def test_should_drop_for_backpressure() -> None:
    """Safety-critical never dropped when dropping below high."""
    assert should_drop_for_backpressure(BACKPRESSURE_PRIORITY_SAFETY_CRITICAL, "high") is False
    assert should_drop_for_backpressure(BACKPRESSURE_PRIORITY_LOW, "high") is True


def test_resume_from() -> None:
    """resume_from returns events after last_event_id."""
    events = [
        {"event_id": "e1", "ts": "1"},
        {"event_id": "e2", "ts": "2"},
        {"event_id": "e3", "ts": "3"},
    ]
    assert len(resume_from(None, events)) == 3
    assert len(resume_from("e2", events)) == 1
    assert resume_from("e2", events)[0]["event_id"] == "e3"
    assert len(resume_from("e9", events)) == 3


def test_chaos_drill_kill_stream(tmp_path: Path) -> None:
    """kill_stream creates stream_disabled.flag."""
    path = kill_stream(tmp_path)
    assert path.endswith("stream_disabled.flag")
    assert (tmp_path / "memory" / "overseer" / "stream_disabled.flag").exists()
    assert "chaos" in (tmp_path / "memory" / "overseer" / "stream_disabled.flag").read_text()


def test_chaos_drill_lag_materializers(tmp_path: Path) -> None:
    """lag_materializers creates materializer_lag.flag."""
    path = lag_materializers(tmp_path)
    assert "materializer_lag.flag" in path
    assert (tmp_path / "memory" / "overseer" / "materializer_lag.flag").exists()


def test_chaos_drill_revoke_bridge_trust_root(tmp_path: Path) -> None:
    """revoke_bridge_trust_root creates marker or renames file."""
    path = revoke_bridge_trust_root(tmp_path)
    assert path
    assert (tmp_path / "memory" / "overseer" / "bridge_trust_revoked.chaos").exists() or "chaos_backup" in path


def test_slo_config_includes_control_surface() -> None:
    """Default SLO config includes stream_freshness and api_availability."""
    config = load_slo_config()
    assert "stream_freshness_max_seconds" in config
    assert "api_availability_min_ratio" in config
    assert config.get("safety_fail_closed_high_impact") is True


def test_check_slos_with_control_metrics() -> None:
    """check_slos runs without error and can breach on stream lag."""
    record_stream_connection()
    record_api_request(success=True)
    record_control_action(attempted=True, denied=False)
    m = get_metrics()
    assert "stream" in m
    assert "api" in m
    assert "controls" in m
    result = check_slos(metrics=m)
    assert "ok" in result
    assert "breaches" in result


def test_heartbeat_constant() -> None:
    """Stream hardening defines heartbeat interval."""
    assert HEARTBEAT_INTERVAL_SECONDS > 0
