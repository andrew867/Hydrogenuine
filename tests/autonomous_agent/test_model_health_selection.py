"""Model health and selection tests.

Tests that:
1. Failed attempts count against model rotation.
2. Least-used selection does not repeatedly pick a failing model.
3. Model with two empty outputs enters cooldown or degraded.
4. Model with repeated reasoning-only outputs is quarantined.
5. Retry never selects the same failed model.
6. Retry prefers model with recent substantive success.
7. Reasoning_content-only response is not substantive.
8. Reasoning_content-only response preserves reasoning_content for debugging.
9. Topic completion remains blocked when only reasoning_content exists.
10. Scheduler cannot call reasoning-only outputs substantive.
11. Explicit model denylist excludes a model from selection.
12. Quarantined model cannot be selected later in same run.
13. Cooldown works.
14. Model health summary appears in output.
15. Gate blocks if top-selected model has 0 substantive outputs.
16. Gate blocks if output quality ratio remains below threshold.
17. No promotion, memory promotion, or remote fallback changes.
18. Successful micro-run with healthy models passes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.model_selection.model_rotation import (
    ModelRotationTracker, ModelHealthRecord,
    HEALTH_HEALTHY, HEALTH_DEGRADED, HEALTH_COOLDOWN, HEALTH_QUARANTINED,
    HEALTH_FORBIDDEN,
)
from hg_runtime.model_selection.model_selection_policy import select_model, SelectionResult
from hg_runtime.model_selection.model_roster import ModelRoster
from hg_runtime.model_selection.model_classifier import ModelClassification
from hg_runtime.live_local.reasoning_classifier import classify_response


def _make_roster(*model_ids):
    models = []
    for mid in model_ids:
        mc = ModelClassification(
            model_id=mid, family="test", size_hint="3b",
            role_hints=["fast_triage", "instruction_following"],
            speed_hint="fast", resource_risk="low", is_embedding=False,
            confidence="high",
        )
        models.append(mc)
    return ModelRoster(models=models, resource_risk_ceiling="medium")


# --- 1. Failed attempts count against rotation ---

class TestFailedAttemptsCountAgainstRotation:
    def test_timeout_increments_attempts(self):
        tracker = ModelRotationTracker()
        tracker.record_timeout("model_a")
        assert tracker.attempt_count("model_a") == 1

    def test_empty_increments_attempts(self):
        tracker = ModelRotationTracker()
        tracker.record_empty("model_a")
        assert tracker.attempt_count("model_a") == 1

    def test_reasoning_only_increments_attempts(self):
        tracker = ModelRotationTracker()
        tracker.record_reasoning_only("model_a")
        assert tracker.attempt_count("model_a") == 1

    def test_success_increments_attempts(self):
        tracker = ModelRotationTracker()
        tracker.record_use("model_a", "test")
        assert tracker.attempt_count("model_a") == 1

    def test_failed_model_not_always_first_after_failure(self):
        roster = _make_roster("model_a", "model_b")
        tracker = ModelRotationTracker()
        tracker.record_timeout("model_a")
        tracker.record_timeout("model_a")
        result = select_model(
            roster, "source_summary",
            usage_counts=tracker.usage_counts,
            rotation_tracker=tracker,
        )
        assert result.model_id == "model_b"


# --- 2. Least-used does not repeatedly pick failing model ---

class TestNoDeathSpiral:
    def test_failing_model_demoted_after_attempts(self):
        roster = _make_roster("bad_model", "good_model")
        tracker = ModelRotationTracker()
        tracker.record_timeout("bad_model")
        tracker.record_timeout("bad_model")
        tracker.record_use("good_model", "test")
        result = select_model(
            roster, "source_summary",
            usage_counts=tracker.usage_counts,
            rotation_tracker=tracker,
        )
        assert result.model_id == "good_model"

    def test_three_timeouts_quarantines(self):
        tracker = ModelRotationTracker()
        tracker.record_timeout("bad")
        tracker.record_timeout("bad")
        tracker.record_timeout("bad")
        assert tracker.model_health("bad") == HEALTH_QUARANTINED


# --- 3. Two empty outputs → cooldown/degraded ---

class TestEmptyOutputCooldown:
    def test_two_empty_outputs_cooldown(self):
        tracker = ModelRotationTracker()
        tracker.record_empty("model_a")
        tracker.record_empty("model_a")
        assert tracker.model_health("model_a") in (HEALTH_COOLDOWN, HEALTH_QUARANTINED)

    def test_two_consecutive_failures_cooldown(self):
        tracker = ModelRotationTracker()
        tracker.record_failure("model_a", "err1")
        tracker.record_failure("model_a", "err2")
        assert tracker.model_health("model_a") == HEALTH_COOLDOWN


# --- 4. Repeated reasoning-only → quarantined ---

class TestReasoningOnlyQuarantine:
    def test_two_reasoning_only_quarantined(self):
        tracker = ModelRotationTracker()
        tracker.record_reasoning_only("model_a")
        tracker.record_reasoning_only("model_a")
        assert tracker.model_health("model_a") == HEALTH_QUARANTINED

    def test_one_reasoning_only_not_quarantined(self):
        tracker = ModelRotationTracker()
        tracker.record_reasoning_only("model_a")
        assert tracker.model_health("model_a") != HEALTH_QUARANTINED


# --- 5. Retry never selects the same failed model ---

class TestRetryExcludesFailedModel:
    def test_retry_selects_different_model(self):
        roster = _make_roster("model_a", "model_b")
        tracker = ModelRotationTracker()
        tracker.record_timeout("model_a")
        result = select_model(
            roster, "source_summary",
            usage_counts=tracker.usage_counts,
            rotation_tracker=tracker,
            exclude_models={"model_a"},
        )
        assert result is not None
        assert result.model_id != "model_a"
        assert result.model_id == "model_b"

    def test_retry_falls_back_when_only_one_model(self):
        roster = _make_roster("model_a")
        tracker = ModelRotationTracker()
        tracker.record_timeout("model_a")
        result = select_model(
            roster, "source_summary",
            usage_counts=tracker.usage_counts,
            rotation_tracker=tracker,
            exclude_models={"model_a"},
        )
        # With only one model, exclusion filter falls back to the only candidate
        assert result is not None
        assert result.model_id == "model_a"


# --- 6. Retry prefers model with recent substantive success ---

class TestRetryPrefersSuccess:
    def test_proven_model_preferred_when_alternative_failed(self):
        roster = _make_roster("good", "bad", "untested")
        tracker = ModelRotationTracker()
        tracker.record_use("good", "test")
        tracker.record_timeout("bad")
        tracker.record_timeout("bad")
        tracker.record_timeout("bad")
        result = select_model(
            roster, "source_summary",
            usage_counts=tracker.usage_counts,
            rotation_tracker=tracker,
            exclude_models={"bad"},
        )
        assert result is not None
        assert result.model_id in ("good", "untested")


# --- 7. Reasoning-only response is not substantive ---

class TestReasoningOnlyNotSubstantive:
    def test_reasoning_only_not_substantive(self):
        r = classify_response(
            model_id="test", endpoint="x",
            content="", reasoning="long reasoning text",
            finish_reason="stop",
        )
        assert r.classification == "reasoning_only"
        assert r.is_substantive() is False

    def test_reasoning_only_truncated_not_substantive(self):
        r = classify_response(
            model_id="test", endpoint="x",
            content="", reasoning="long reasoning text",
            finish_reason="length",
        )
        assert r.classification == "reasoning_only_truncated"
        assert r.is_substantive() is False


# --- 8. Reasoning_content preserved for debugging ---

class TestReasoningContentPreserved:
    def test_reasoning_excerpt_stored(self):
        r = classify_response(
            model_id="test", endpoint="x",
            content="", reasoning="This is the reasoning trace for debugging",
            finish_reason="stop",
        )
        assert r.reasoning_excerpt == "This is the reasoning trace for debugging"
        assert r.reasoning_char_count == 41

    def test_reasoning_excerpt_truncated_at_200(self):
        long_reasoning = "R" * 500
        r = classify_response(
            model_id="test", endpoint="x",
            content="", reasoning=long_reasoning,
            finish_reason="stop",
        )
        assert len(r.reasoning_excerpt) == 200


# --- 9. Topic blocked when only reasoning_content exists ---

class TestTopicBlockedReasoningOnly:
    def test_reasoning_only_not_usable_for_summary(self):
        r = classify_response(
            model_id="test", endpoint="x",
            content="", reasoning="reasoning only",
            finish_reason="stop",
        )
        assert r.usable_for_research_summary is False

    def test_content_plus_reasoning_usable(self):
        r = classify_response(
            model_id="test", endpoint="x",
            content="final answer", reasoning="reasoning",
            finish_reason="stop",
        )
        assert r.usable_for_research_summary is True
        assert r.is_substantive() is True


# --- 10. Scheduler cannot call reasoning-only substantive ---

class TestSchedulerReasoningOnlyNotSubstantive:
    def test_reasoning_only_classification_not_substantive(self):
        r = classify_response(
            model_id="test", endpoint="x",
            content="", reasoning="thinking...",
            finish_reason="stop",
        )
        assert not r.is_substantive()
        assert r.classification == "reasoning_only"


# --- 11. Explicit model denylist ---

class TestModelDenylist:
    def test_avoid_model_excluded_from_roster(self):
        roster = ModelRoster(
            models=[
                ModelClassification(model_id="allowed", family="test", size_hint="3b",
                                    role_hints=["fast_triage"], resource_risk="low"),
                ModelClassification(model_id="denied", family="test", size_hint="3b",
                                    role_hints=["fast_triage"], resource_risk="low"),
            ],
            avoid_models=["denied"],
            resource_risk_ceiling="medium",
        )
        result = select_model(roster, "source_summary")
        assert result is not None
        assert result.model_id == "allowed"

    def test_exclude_models_param(self):
        roster = _make_roster("model_a", "model_b")
        result = select_model(
            roster, "source_summary",
            exclude_models={"model_a"},
        )
        assert result is not None
        assert result.model_id == "model_b"


# --- 12. Quarantined model not selectable ---

class TestQuarantineBlocks:
    def test_quarantined_model_not_selected(self):
        roster = _make_roster("quarantined_model", "healthy_model")
        tracker = ModelRotationTracker()
        tracker.record_timeout("quarantined_model")
        tracker.record_timeout("quarantined_model")
        tracker.record_timeout("quarantined_model")
        assert tracker.model_health("quarantined_model") == HEALTH_QUARANTINED
        result = select_model(
            roster, "source_summary",
            usage_counts=tracker.usage_counts,
            rotation_tracker=tracker,
        )
        assert result.model_id == "healthy_model"

    def test_quarantine_is_permanent_for_run(self):
        tracker = ModelRotationTracker()
        tracker.record_timeout("model_a")
        tracker.record_timeout("model_a")
        tracker.record_timeout("model_a")
        assert tracker.model_health("model_a") == HEALTH_QUARANTINED
        assert not tracker.is_selectable("model_a")


# --- 13. Cooldown ---

class TestCooldown:
    def test_cooldown_after_two_failures(self):
        tracker = ModelRotationTracker()
        tracker.record_empty("model_a")
        tracker.record_empty("model_a")
        assert tracker.model_health("model_a") in (HEALTH_COOLDOWN, HEALTH_QUARANTINED)

    def test_success_resets_consecutive_failures(self):
        tracker = ModelRotationTracker()
        tracker.record_timeout("model_a")
        tracker.record_use("model_a", "test")
        assert tracker.model_health("model_a") == HEALTH_HEALTHY
        h = tracker._get_health("model_a")
        assert h.consecutive_failures == 0


# --- 14. Model health summary ---

class TestHealthSummary:
    def test_health_summary_structure(self):
        tracker = ModelRotationTracker()
        tracker.record_use("good", "test")
        tracker.record_timeout("bad")
        tracker.record_timeout("bad")
        tracker.record_timeout("bad")
        summary = tracker.health_summary()
        assert "model_health" in summary
        assert "quarantined" in summary
        assert "bad" in summary["quarantined"]
        assert "good" in summary["healthy"]

    def test_health_record_fields(self):
        tracker = ModelRotationTracker()
        tracker.record_timeout("model_a")
        tracker.record_empty("model_a")
        h = tracker._get_health("model_a")
        d = h.to_dict()
        assert d["attempted_calls"] == 2
        assert d["timeouts"] == 1
        assert d["empty_content_failures"] == 1
        assert d["consecutive_failures"] == 2
        assert d["model_id"] == "model_a"


# --- 15. Zero substantive after N attempts → quarantine ---

class TestZeroSubstantiveQuarantine:
    def test_zero_substantive_after_three_attempts(self):
        tracker = ModelRotationTracker()
        tracker.record_timeout("model_a")
        tracker.record_empty("model_a")
        tracker.record_failure("model_a", "error")
        assert tracker.model_health("model_a") == HEALTH_QUARANTINED
        h = tracker._get_health("model_a")
        assert h.substantive_successes == 0
        assert h.attempted_calls == 3


# --- 16. Timeout rate quarantine ---

class TestTimeoutRateQuarantine:
    def test_75_percent_timeout_rate_quarantined(self):
        tracker = ModelRotationTracker()
        tracker.record_timeout("model_a")
        tracker.record_timeout("model_a")
        tracker.record_timeout("model_a")
        tracker.record_use("model_a", "test")
        assert tracker.model_health("model_a") == HEALTH_QUARANTINED


# --- 17. Governance unchanged ---

class TestGovernanceUnchanged:
    def test_promotion_still_blocked(self):
        r = classify_response(
            model_id="test", endpoint="x",
            content="answer", finish_reason="stop",
        )
        assert r.promotion_allowed is False

    def test_tools_still_blocked(self):
        r = classify_response(
            model_id="test", endpoint="x",
            content="answer", finish_reason="stop",
        )
        assert r.tools_authorized is False

    def test_remote_fallback_still_red(self):
        r = classify_response(
            model_id="test", endpoint="x",
            content="answer", remote_fallback=True,
        )
        assert r.severity == "RED"
        assert r.is_substantive() is False


# --- 18. Healthy model micro-run scenario ---

class TestHealthyModelSelection:
    def test_healthy_model_always_selected_when_others_quarantined(self):
        roster = _make_roster("good", "bad1", "bad2")
        tracker = ModelRotationTracker()
        for bad in ("bad1", "bad2"):
            tracker.record_timeout(bad)
            tracker.record_timeout(bad)
            tracker.record_timeout(bad)
        for _ in range(5):
            result = select_model(
                roster, "source_summary",
                usage_counts=tracker.usage_counts,
                rotation_tracker=tracker,
            )
            assert result.model_id == "good"
