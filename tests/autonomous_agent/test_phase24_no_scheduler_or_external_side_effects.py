"""Phase 24 no scheduler or external side effects."""
from __future__ import annotations

from hg_runtime.overnight_field_run.field_run_config import OvernightFieldRunConfig, validate_field_run_config
from hg_runtime.overnight_field_run.schema import load_field_run_policy


def test_policy_forbids_scheduler():
    p = load_field_run_policy()
    assert p["cron_allowed"] is False
    assert p["daemon_allowed"] is False
    assert p["auto_respawn_allowed"] is False


def test_config_forbids_live_writes():
    with __import__("pytest").raises(Exception):
        validate_field_run_config(
            OvernightFieldRunConfig(
                field_run_id="x",
                agent_id="zero",
                live_writes_allowed=True,
                created_at="2026-01-01T00:00:00+00:00",
            ),
            production_mode=False,
        )
