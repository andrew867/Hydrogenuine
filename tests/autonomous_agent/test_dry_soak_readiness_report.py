"""Dry soak readiness report tests."""
from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.dry_soak.readiness_report import build_readiness_report, compute_readiness_verdict
from hg_runtime.dry_soak.schema import (
    DrySoakRun,
    DrySoakRunStatus,
    DrySoakTurnSummary,
    DrySoakVerdict,
    ReadinessVerdict,
)


def test_readiness_report_generated_fields():
    run = DrySoakRun(
        run_id="r1",
        agent_id="zero",
        started_at="2026-06-18T00:00:00+00:00",
        status=DrySoakRunStatus.COMPLETED,
        config_hash="abc",
        turn_count=2,
        turn_summaries=[
            DrySoakTurnSummary(turn_index=1, turn_receipt_ref="ref1", verdict="GREEN"),
            DrySoakTurnSummary(turn_index=2, turn_receipt_ref="ref2", verdict="GREEN"),
        ],
        verdict=DrySoakVerdict.GREEN_DRY_SOAK_COMPLETE,
    ).with_hash()
    report = build_readiness_report(
        run=run,
        duration_seconds=120.0,
        provider_status="unavailable",
        live_read_status="unavailable",
        replay_status="GREEN_REPLAY_OK",
        artifact_count=0,
        review_queue_count=0,
        duplication_verdict="GREEN_DUPLICATION_OK",
        resource_verdict="GREEN_RESOURCE_OK",
        failure_budget_verdict="GREEN_BUDGET_OK",
        external_side_effects=False,
        target_duration_seconds=1800,
    )
    assert report.readiness_verdict == ReadinessVerdict.YELLOW_READY_WITH_PROVIDER_OR_CREDENTIAL_LIMITS


def test_short_duration_yellow():
    verdict = compute_readiness_verdict(
        dry_soak_verdict=DrySoakVerdict.GREEN_DRY_SOAK_COMPLETE,
        provider_status="available",
        live_read_status="available",
        duration_seconds=100,
        target_duration_seconds=1800,
        external_side_effects=False,
    )
    assert verdict == ReadinessVerdict.YELLOW_READY_WITH_SHORT_DURATION_ONLY
