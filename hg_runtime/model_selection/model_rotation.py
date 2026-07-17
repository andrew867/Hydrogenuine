"""Model rotation tracker with health tracking.

Tracks model usage, failures, and health status. Failed attempts count
against selection priority. Chronically failing models are quarantined.
No model authority. No consensus as proof.
"""

from __future__ import annotations

from dataclasses import dataclass, field

HEALTH_HEALTHY = "healthy"
HEALTH_DEGRADED = "degraded"
HEALTH_COOLDOWN = "cooldown"
HEALTH_QUARANTINED = "quarantined"
HEALTH_FORBIDDEN = "forbidden_by_policy"

QUARANTINE_CONSECUTIVE = 3
QUARANTINE_ZERO_AFTER_N = 3
QUARANTINE_REASONING_ONLY = 2
QUARANTINE_TIMEOUT_RATE = 0.75
QUARANTINE_TIMEOUT_MIN_ATTEMPTS = 4
COOLDOWN_THRESHOLD = 2
DEGRADED_CONSECUTIVE = 2


@dataclass
class ModelHealthRecord:
    model_id: str = ""
    attempted_calls: int = 0
    substantive_successes: int = 0
    empty_content_failures: int = 0
    reasoning_only_failures: int = 0
    timeouts: int = 0
    provider_errors: int = 0
    parse_errors: int = 0
    prompt_echo_failures: int = 0
    truncated_substantive: int = 0
    consecutive_failures: int = 0
    last_failure_reason: str = ""
    health: str = HEALTH_HEALTHY

    def _recompute_health(self) -> None:
        if self.health == HEALTH_FORBIDDEN:
            return
        if self.health == HEALTH_QUARANTINED:
            return

        if self.consecutive_failures >= QUARANTINE_CONSECUTIVE:
            self.health = HEALTH_QUARANTINED
            return
        if (self.attempted_calls >= QUARANTINE_ZERO_AFTER_N
                and self.substantive_successes == 0):
            self.health = HEALTH_QUARANTINED
            return
        if self.reasoning_only_failures >= QUARANTINE_REASONING_ONLY:
            self.health = HEALTH_QUARANTINED
            return
        if (self.attempted_calls >= QUARANTINE_TIMEOUT_MIN_ATTEMPTS
                and self.attempted_calls > 0
                and self.timeouts / self.attempted_calls >= QUARANTINE_TIMEOUT_RATE):
            self.health = HEALTH_QUARANTINED
            return

        non_substantive = (self.empty_content_failures + self.reasoning_only_failures
                           + self.timeouts + self.provider_errors)
        if self.consecutive_failures >= COOLDOWN_THRESHOLD:
            self.health = HEALTH_COOLDOWN
            return
        if non_substantive >= COOLDOWN_THRESHOLD and self.substantive_successes == 0:
            self.health = HEALTH_COOLDOWN
            return

        if self.consecutive_failures >= DEGRADED_CONSECUTIVE:
            self.health = HEALTH_DEGRADED
            return

        self.health = HEALTH_HEALTHY

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "attempted_calls": self.attempted_calls,
            "substantive_successes": self.substantive_successes,
            "empty_content_failures": self.empty_content_failures,
            "reasoning_only_failures": self.reasoning_only_failures,
            "timeouts": self.timeouts,
            "provider_errors": self.provider_errors,
            "parse_errors": self.parse_errors,
            "prompt_echo_failures": self.prompt_echo_failures,
            "truncated_substantive": self.truncated_substantive,
            "consecutive_failures": self.consecutive_failures,
            "last_failure_reason": self.last_failure_reason,
            "health": self.health,
        }


@dataclass
class ModelRotationTracker:
    usage_counts: dict[str, int] = field(default_factory=dict)
    intent_usage: dict[str, list[str]] = field(default_factory=dict)
    failures: dict[str, int] = field(default_factory=dict)
    timeouts: dict[str, int] = field(default_factory=dict)
    timeout_cooldown: set[str] = field(default_factory=set)
    cooldown_threshold: int = COOLDOWN_THRESHOLD
    _health: dict[str, ModelHealthRecord] = field(default_factory=dict)

    def _get_health(self, model_id: str) -> ModelHealthRecord:
        if model_id not in self._health:
            self._health[model_id] = ModelHealthRecord(model_id=model_id)
        return self._health[model_id]

    def record_use(self, model_id: str, intent: str) -> None:
        self.usage_counts[model_id] = self.usage_counts.get(model_id, 0) + 1
        self.intent_usage.setdefault(intent, []).append(model_id)
        h = self._get_health(model_id)
        h.attempted_calls += 1
        h.substantive_successes += 1
        h.consecutive_failures = 0
        h.last_failure_reason = ""
        h._recompute_health()

    def record_failure(self, model_id: str, reason: str = "provider_error") -> None:
        self.failures[model_id] = self.failures.get(model_id, 0) + 1
        h = self._get_health(model_id)
        h.attempted_calls += 1
        h.consecutive_failures += 1
        h.last_failure_reason = reason
        h.provider_errors += 1
        h._recompute_health()

    def record_timeout(self, model_id: str) -> None:
        self.timeouts[model_id] = self.timeouts.get(model_id, 0) + 1
        if self.timeouts[model_id] >= self.cooldown_threshold:
            self.timeout_cooldown.add(model_id)
        h = self._get_health(model_id)
        h.attempted_calls += 1
        h.consecutive_failures += 1
        h.timeouts += 1
        h.last_failure_reason = "timeout"
        h._recompute_health()

    def record_empty(self, model_id: str) -> None:
        self.failures[model_id] = self.failures.get(model_id, 0) + 1
        h = self._get_health(model_id)
        h.attempted_calls += 1
        h.consecutive_failures += 1
        h.empty_content_failures += 1
        h.last_failure_reason = "empty_content"
        h._recompute_health()

    def record_reasoning_only(self, model_id: str) -> None:
        self.failures[model_id] = self.failures.get(model_id, 0) + 1
        h = self._get_health(model_id)
        h.attempted_calls += 1
        h.consecutive_failures += 1
        h.reasoning_only_failures += 1
        h.last_failure_reason = "reasoning_only"
        h._recompute_health()

    def model_health(self, model_id: str) -> str:
        return self._get_health(model_id).health

    def is_selectable(self, model_id: str) -> bool:
        h = self.model_health(model_id)
        return h not in (HEALTH_QUARANTINED, HEALTH_FORBIDDEN)

    def attempt_count(self, model_id: str) -> int:
        return self._get_health(model_id).attempted_calls

    def has_recent_success(self, model_id: str) -> bool:
        h = self._get_health(model_id)
        return h.substantive_successes > 0

    def distinct_models_used(self) -> int:
        return len(self.usage_counts)

    def variation_summary(self) -> dict:
        return {
            "distinct_models_used": self.distinct_models_used(),
            "usage_counts": dict(self.usage_counts),
            "failures": dict(self.failures),
            "timeouts": dict(self.timeouts),
            "cooled_down": sorted(self.timeout_cooldown),
            "model_selection_is_not_authority": True,
            "consensus_is_not_proof": True,
            "disagreement_is_not_disproof": True,
            "promotion_allowed": False,
        }

    def health_summary(self) -> dict:
        return {
            "model_health": {mid: h.to_dict() for mid, h in self._health.items()},
            "quarantined": sorted(m for m, h in self._health.items()
                                  if h.health == HEALTH_QUARANTINED),
            "cooldown": sorted(m for m, h in self._health.items()
                               if h.health == HEALTH_COOLDOWN),
            "degraded": sorted(m for m, h in self._health.items()
                               if h.health == HEALTH_DEGRADED),
            "healthy": sorted(m for m, h in self._health.items()
                              if h.health == HEALTH_HEALTHY),
            "model_selection_is_not_authority": True,
            "promotion_allowed": False,
        }

    def variation_possible_reason(self, available_count: int, min_distinct: int) -> str:
        if available_count < min_distinct:
            return "not_enough_available_models"
        if available_count == 1:
            return "only_one_model_available"
        if self.distinct_models_used() >= min_distinct:
            return "variation_achieved"
        return "variation_possible"
