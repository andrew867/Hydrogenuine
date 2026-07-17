"""
Drift detector: assess turn context for constraint violation, behavioral divergence,
runaway, and safety anomalies. Pure and unit-testable; no I/O.
Pack 10: replaces stub with deterministic counters and thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Severity(str, Enum):
    LOW = "LOW"
    MED = "MED"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RecommendedAction(str, Enum):
    NONE = "none"
    PAUSE = "pause"
    QUARANTINE = "quarantine"


# Signal identifiers for drift assessment
SIGNAL_CONSTRAINT_VIOLATION = "constraint_violation"
SIGNAL_BEHAVIORAL_DIVERGENCE = "behavioral_divergence"
SIGNAL_RUNAWAY = "runaway"
SIGNAL_SAFETY_ANOMALY = "safety_anomaly"


@dataclass
class TurnContext:
    """Context for a single turn used by the drift detector."""

    tenant_id: str
    chat_id: str
    agent_id: str
    recent_message_count: int = 0
    recent_tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    policy_denial_count: int = 0
    consecutive_error_count: int = 0
    last_tool_names: List[str] = field(default_factory=list)
    disallowed_tool_attempts: List[str] = field(default_factory=list)
    total_tokens_or_chars_estimate: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "chat_id": self.chat_id,
            "agent_id": self.agent_id,
            "recent_message_count": self.recent_message_count,
            "recent_tool_calls": self.recent_tool_calls,
            "policy_denial_count": self.policy_denial_count,
            "consecutive_error_count": self.consecutive_error_count,
            "last_tool_names": self.last_tool_names,
            "disallowed_tool_attempts": self.disallowed_tool_attempts,
            "total_tokens_or_chars_estimate": self.total_tokens_or_chars_estimate,
        }


@dataclass
class DriftAssessment:
    """Result of drift assessment: signals, severity, and recommended action."""

    signals: List[str]
    severity: Severity
    recommended_action: RecommendedAction
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signals": self.signals,
            "severity": self.severity.value,
            "recommended_action": self.recommended_action.value,
            "details": self.details,
        }


class DriftDetector:
    """
    Deterministic drift detector using configurable thresholds.
    No I/O; suitable for unit tests and production.
    """

    def __init__(
        self,
        *,
        max_recent_messages_before_warn: int = 200,
        policy_denials_med_threshold: int = 3,
        policy_denials_high_threshold: int = 5,
        consecutive_errors_med_threshold: int = 2,
        consecutive_errors_high_threshold: int = 4,
        disallowed_tool_quarantine_threshold: int = 1,
        runaway_chars_estimate_threshold: int = 100_000,
    ) -> None:
        self.max_recent_messages_before_warn = max_recent_messages_before_warn
        self.policy_denials_med_threshold = policy_denials_med_threshold
        self.policy_denials_high_threshold = policy_denials_high_threshold
        self.consecutive_errors_med_threshold = consecutive_errors_med_threshold
        self.consecutive_errors_high_threshold = consecutive_errors_high_threshold
        self.disallowed_tool_quarantine_threshold = disallowed_tool_quarantine_threshold
        self.runaway_chars_estimate_threshold = runaway_chars_estimate_threshold

    def assess(self, turn_context: TurnContext) -> DriftAssessment:
        """
        Assess turn context for drift signals and return severity and recommended action.
        """
        signals: List[str] = []
        details: Dict[str, Any] = {}

        # Constraint violation: disallowed tool attempts
        if turn_context.disallowed_tool_attempts:
            signals.append(SIGNAL_CONSTRAINT_VIOLATION)
            details["disallowed_tool_attempts"] = turn_context.disallowed_tool_attempts
            if len(turn_context.disallowed_tool_attempts) >= self.disallowed_tool_quarantine_threshold:
                return DriftAssessment(
                    signals=signals,
                    severity=Severity.CRITICAL,
                    recommended_action=RecommendedAction.QUARANTINE,
                    details=details,
                )

        # Runaway: excessive output size
        if turn_context.total_tokens_or_chars_estimate >= self.runaway_chars_estimate_threshold:
            signals.append(SIGNAL_RUNAWAY)
            details["total_tokens_or_chars_estimate"] = turn_context.total_tokens_or_chars_estimate
            details["threshold"] = self.runaway_chars_estimate_threshold
            return DriftAssessment(
                signals=signals,
                severity=Severity.HIGH,
                recommended_action=RecommendedAction.PAUSE,
                details=details,
            )

        # Behavioral divergence / safety: repeated policy denials
        if turn_context.policy_denial_count >= self.policy_denials_high_threshold:
            signals.append(SIGNAL_BEHAVIORAL_DIVERGENCE)
            signals.append(SIGNAL_SAFETY_ANOMALY)
            details["policy_denial_count"] = turn_context.policy_denial_count
            return DriftAssessment(
                signals=signals,
                severity=Severity.HIGH,
                recommended_action=RecommendedAction.QUARANTINE,
                details=details,
            )
        if turn_context.policy_denial_count >= self.policy_denials_med_threshold:
            signals.append(SIGNAL_BEHAVIORAL_DIVERGENCE)
            details["policy_denial_count"] = turn_context.policy_denial_count
            return DriftAssessment(
                signals=signals,
                severity=Severity.MED,
                recommended_action=RecommendedAction.PAUSE,
                details=details,
            )

        # Consecutive errors
        if turn_context.consecutive_error_count >= self.consecutive_errors_high_threshold:
            signals.append(SIGNAL_SAFETY_ANOMALY)
            details["consecutive_error_count"] = turn_context.consecutive_error_count
            return DriftAssessment(
                signals=signals,
                severity=Severity.HIGH,
                recommended_action=RecommendedAction.PAUSE,
                details=details,
            )
        if turn_context.consecutive_error_count >= self.consecutive_errors_med_threshold:
            signals.append(SIGNAL_SAFETY_ANOMALY)
            details["consecutive_error_count"] = turn_context.consecutive_error_count
            return DriftAssessment(
                signals=signals,
                severity=Severity.MED,
                recommended_action=RecommendedAction.PAUSE,
                details=details,
            )

        # Message volume (behavioral divergence)
        if turn_context.recent_message_count >= self.max_recent_messages_before_warn:
            signals.append(SIGNAL_BEHAVIORAL_DIVERGENCE)
            details["recent_message_count"] = turn_context.recent_message_count
            return DriftAssessment(
                signals=signals,
                severity=Severity.LOW,
                recommended_action=RecommendedAction.NONE,
                details=details,
            )

        return DriftAssessment(
            signals=[],
            severity=Severity.LOW,
            recommended_action=RecommendedAction.NONE,
            details={},
        )


def get_default_detector() -> DriftDetector:
    """Return a detector with default thresholds."""
    return DriftDetector()
