from operator_console.server.app.services.confidence_summary import build_confidence_summary


def test_build_confidence_summary_is_confident_when_core_signals_align():
    summary = build_confidence_summary(
        self_model_summary={
            "status": "healthy",
            "dominant_uncertainty": "confident",
            "relationship_signal": "respect",
        },
        presence_initiative_summary={
            "status": "healthy",
            "trust_band": 3,
            "agency_budget": 11.0,
        },
        continuity_recovery_readiness={"status": "ready", "acknowledged": True, "recovery_closeout_complete": True},
        operational_resume_governance_summary={"status": "ready"},
        operational_resume_checkpoint={"approved": True},
        bounded_autonomy_policy_summary={"status": "ready"},
        commitment_summary={"count": 1, "open_count": 0, "overdue_count": 0},
        identity_continuity_summary={"status": "healthy"},
    )

    assert summary["status"] == "healthy"
    assert summary["confidence_level"] in {"confident", "certain"}
    assert summary["confidence_score"] >= 80
    assert "self_model_healthy" in summary["confidence_drivers"]


def test_build_confidence_summary_reacts_to_missing_signals():
    summary = build_confidence_summary(
        self_model_summary={"status": "missing"},
        presence_initiative_summary={"status": "missing"},
        continuity_recovery_readiness={"status": "blocked"},
        operational_resume_governance_summary={"status": "blocked"},
        operational_resume_checkpoint={"approved": False},
        bounded_autonomy_policy_summary={"status": "blocked"},
        commitment_summary={"count": 0, "open_count": 0, "overdue_count": 0},
        identity_continuity_summary={"status": "missing"},
    )

    assert summary["status"] == "missing"
    assert summary["confidence_level"] == "uncertain"
    assert summary["confidence_score"] < 50
    assert "self_model_missing" in summary["confidence_blockers"]


def test_build_confidence_summary_reacts_to_drift_watch():
    summary = build_confidence_summary(
        self_model_summary={"status": "healthy"},
        presence_initiative_summary={"status": "healthy", "trust_band": 2},
        continuity_recovery_readiness={"status": "ready"},
        operational_resume_governance_summary={"status": "ready"},
        operational_resume_checkpoint={"approved": True},
        bounded_autonomy_policy_summary={"status": "ready"},
        commitment_summary={"count": 1, "open_count": 0, "overdue_count": 0},
        identity_continuity_summary={"status": "healthy"},
        drift_summary={"status": "watch", "max_score": 0.8, "active_safeguards": []},
    )

    assert summary["confidence_score"] < 100
    assert "drift_watch" in summary["confidence_cautions"]


def test_build_confidence_summary_reacts_to_mimicry_and_continuity_quality():
    summary = build_confidence_summary(
        self_model_summary={"status": "healthy"},
        presence_initiative_summary={"status": "healthy", "trust_band": 2},
        continuity_recovery_readiness={"status": "ready"},
        operational_resume_governance_summary={"status": "ready"},
        operational_resume_checkpoint={"approved": True},
        bounded_autonomy_policy_summary={"status": "ready"},
        commitment_summary={"count": 1, "open_count": 0, "overdue_count": 0},
        identity_continuity_summary={"status": "healthy"},
        mimicry_control_summary={
            "status": "ready",
            "voice_belief_separated": True,
            "grounding_required": True,
            "safeguard_summary": {"grounded": True},
        },
        continuity_quality_summary={
            "status": "healthy",
            "quality_score": 88,
            "operator_override_rate": 0.1,
            "promotion_accuracy": 0.82,
        },
    )

    assert summary["status"] == "healthy"
    assert summary["confidence_score"] >= 80
    assert "mimicry_ready" in summary["confidence_drivers"]
    assert "continuity_quality_healthy" in summary["confidence_drivers"]
