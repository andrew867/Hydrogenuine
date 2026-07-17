"""
Tests for hg_core.control.drift_detector: DriftDetector.assess, TurnContext, DriftAssessment.
Pack 10: no mocks; deterministic thresholds.
"""

import pytest

from hg_core.control.drift_detector import (
    DriftAssessment,
    DriftDetector,
    RecommendedAction,
    Severity,
    TurnContext,
    get_default_detector,
    SIGNAL_CONSTRAINT_VIOLATION,
    SIGNAL_BEHAVIORAL_DIVERGENCE,
    SIGNAL_RUNAWAY,
    SIGNAL_SAFETY_ANOMALY,
)


def test_no_drift_returns_low_none():
    """Clean context yields LOW severity and recommended_action NONE."""
    detector = get_default_detector()
    ctx = TurnContext(tenant_id="t1", chat_id="c1", agent_id="primary")
    out = detector.assess(ctx)
    assert isinstance(out, DriftAssessment)
    assert out.severity == Severity.LOW
    assert out.recommended_action == RecommendedAction.NONE
    assert out.signals == []


def test_disallowed_tool_attempts_quarantine():
    """One or more disallowed tool attempts triggers CRITICAL and QUARANTINE."""
    detector = DriftDetector(disallowed_tool_quarantine_threshold=1)
    ctx = TurnContext(
        tenant_id="t1",
        chat_id="c1",
        agent_id="primary",
        disallowed_tool_attempts=["dangerous_tool"],
    )
    out = detector.assess(ctx)
    assert SIGNAL_CONSTRAINT_VIOLATION in out.signals
    assert out.severity == Severity.CRITICAL
    assert out.recommended_action == RecommendedAction.QUARANTINE
    assert "disallowed_tool_attempts" in out.details


def test_runaway_chars_high_pause():
    """Total chars above threshold triggers RUNAWAY and PAUSE."""
    detector = DriftDetector(runaway_chars_estimate_threshold=100_000)
    ctx = TurnContext(
        tenant_id="t1",
        chat_id="c1",
        agent_id="primary",
        total_tokens_or_chars_estimate=150_000,
    )
    out = detector.assess(ctx)
    assert SIGNAL_RUNAWAY in out.signals
    assert out.severity == Severity.HIGH
    assert out.recommended_action == RecommendedAction.PAUSE


def test_policy_denials_high_quarantine():
    """Policy denials at or above high threshold trigger QUARANTINE."""
    detector = DriftDetector(policy_denials_high_threshold=5)
    ctx = TurnContext(
        tenant_id="t1",
        chat_id="c1",
        agent_id="primary",
        policy_denial_count=5,
    )
    out = detector.assess(ctx)
    assert SIGNAL_BEHAVIORAL_DIVERGENCE in out.signals
    assert SIGNAL_SAFETY_ANOMALY in out.signals
    assert out.severity == Severity.HIGH
    assert out.recommended_action == RecommendedAction.QUARANTINE


def test_policy_denials_med_pause():
    """Policy denials at med threshold trigger MED and PAUSE."""
    detector = DriftDetector(
        policy_denials_med_threshold=3,
        policy_denials_high_threshold=5,
    )
    ctx = TurnContext(
        tenant_id="t1",
        chat_id="c1",
        agent_id="primary",
        policy_denial_count=3,
    )
    out = detector.assess(ctx)
    assert out.severity == Severity.MED
    assert out.recommended_action == RecommendedAction.PAUSE


def test_consecutive_errors_high_pause():
    """Consecutive errors at high threshold trigger SAFETY_ANOMALY and PAUSE."""
    detector = DriftDetector(consecutive_errors_high_threshold=4)
    ctx = TurnContext(
        tenant_id="t1",
        chat_id="c1",
        agent_id="primary",
        consecutive_error_count=4,
    )
    out = detector.assess(ctx)
    assert SIGNAL_SAFETY_ANOMALY in out.signals
    assert out.severity == Severity.HIGH
    assert out.recommended_action == RecommendedAction.PAUSE


def test_consecutive_errors_med_pause():
    """Consecutive errors at med threshold trigger MED and PAUSE."""
    detector = DriftDetector(
        consecutive_errors_med_threshold=2,
        consecutive_errors_high_threshold=4,
    )
    ctx = TurnContext(
        tenant_id="t1",
        chat_id="c1",
        agent_id="primary",
        consecutive_error_count=2,
    )
    out = detector.assess(ctx)
    assert out.severity == Severity.MED
    assert out.recommended_action == RecommendedAction.PAUSE


def test_recent_message_count_low_none():
    """High message count only triggers LOW and NONE (behavioral divergence signal)."""
    detector = DriftDetector(max_recent_messages_before_warn=200)
    ctx = TurnContext(
        tenant_id="t1",
        chat_id="c1",
        agent_id="primary",
        recent_message_count=200,
    )
    out = detector.assess(ctx)
    assert SIGNAL_BEHAVIORAL_DIVERGENCE in out.signals
    assert out.severity == Severity.LOW
    assert out.recommended_action == RecommendedAction.NONE


def test_assessment_to_dict():
    """DriftAssessment.to_dict() is JSON-serializable and includes all fields."""
    detector = get_default_detector()
    ctx = TurnContext(
        tenant_id="t1",
        chat_id="c1",
        agent_id="primary",
        disallowed_tool_attempts=["x"],
    )
    out = detector.assess(ctx)
    d = out.to_dict()
    assert "signals" in d
    assert "severity" in d
    assert "recommended_action" in d
    assert "details" in d
    assert d["severity"] == "CRITICAL"
    assert d["recommended_action"] == "quarantine"


def test_turn_context_to_dict():
    """TurnContext.to_dict() is JSON-serializable."""
    ctx = TurnContext(
        tenant_id="t1",
        chat_id="c2",
        agent_id="primary",
        recent_message_count=10,
    )
    d = ctx.to_dict()
    assert d["tenant_id"] == "t1"
    assert d["chat_id"] == "c2"
    assert d["agent_id"] == "primary"
    assert d["recent_message_count"] == 10
