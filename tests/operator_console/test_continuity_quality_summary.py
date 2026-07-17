from operator_console.server.app.services.continuity_incident_summary import (
    build_continuity_quality_overview,
    build_continuity_quality_summary,
)


def test_build_continuity_quality_summary_is_healthy_when_continuity_artifacts_align():
    summary = build_continuity_quality_summary(
        identity_continuity_summary={
            "status": "healthy",
            "wake_receipt_present": True,
            "sleep_summary_present": True,
        },
        continuity_incident_summary={
            "status": "clean",
            "latest_event_at": "2026-03-24T00:00:00Z",
        },
        continuity_recovery_readiness={
            "status": "ready",
            "acknowledged": True,
            "acknowledged_at": "2026-03-24T00:05:00Z",
        },
        continuity_repair_plan={"status": "healthy"},
        continuity_repair_observation={
            "observation_required": True,
            "observation_complete": True,
            "latest_observed_at": "2026-03-24T00:06:00Z",
            "status": "observed",
        },
        post_rebuild_continuity_check={
            "verification_required": True,
            "verified": True,
            "verified_at": "2026-03-24T00:07:00Z",
            "status": "verified",
        },
        identity_restore_validation={
            "required": True,
            "verified": True,
            "verified_at": "2026-03-24T00:08:00Z",
            "status": "verified",
        },
        supervised_resume_validation={
            "required": True,
            "validated": True,
            "validated_at": "2026-03-24T00:09:00Z",
            "status": "validated",
        },
        review_handoff_summary={
            "release_ready": True,
            "release_blockers": [],
            "latest": {"approval_id": "approval-1"},
        },
        drift_review_summary={"status": "healthy"},
        evidence_timeline_summary={"counts": {"continuity_events": 2, "approval_events": 1}},
    )

    assert summary["status"] == "healthy"
    assert summary["quality_score"] >= 80
    assert summary["coverage_score"] > 0.8
    assert summary["attribution_score"] > 0.7
    assert summary["operator_override_rate"] > 0
    assert summary["promotion_accuracy"] > 0


def test_build_continuity_quality_overview_rolls_up_entity_scores():
    overview = build_continuity_quality_overview(
        [
            {"id": "one", "display_name": "One", "continuity_quality_summary": {"status": "healthy", "quality_score": 91}},
            {"id": "two", "display_name": "Two", "continuity_quality_summary": {"status": "watch", "quality_score": 62}},
            {"id": "three", "display_name": "Three", "continuity_quality_summary": {"status": "blocked", "quality_score": 41}},
        ]
    )

    assert overview["status"] == "blocked"
    assert overview["entity_count"] == 3
    assert overview["healthy_count"] == 1
    assert overview["watch_count"] == 1
    assert overview["blocked_count"] == 1
    assert overview["average_quality_score"] > 0
    assert overview["worst_entities"][0]["entity_id"] == "three"
