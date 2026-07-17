"""Budget tracker for overnight research runs.

Tracks sources, model calls, screenshots consumed vs limits.
No promotion. Operator review required.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ResearchBudget:
    max_total_sources: int = 20
    max_total_model_calls: int = 40
    max_total_screenshots: int = 10
    max_backlog_topics: int = 5
    per_topic_max_sources: int = 2
    per_topic_max_model_calls: int = 4
    per_topic_max_screenshots: int = 1
    reserve_final_report_budget: bool = True

    sources_used: int = 0
    model_calls_used: int = 0
    screenshots_used: int = 0
    topics_started: int = 0
    topics_completed: int = 0

    def remaining_sources(self) -> int:
        return max(0, self.max_total_sources - self.sources_used)

    def remaining_model_calls(self) -> int:
        return max(0, self.max_total_model_calls - self.model_calls_used)

    def remaining_screenshots(self) -> int:
        return max(0, self.max_total_screenshots - self.screenshots_used)

    def remaining_topics(self) -> int:
        return max(0, self.max_backlog_topics - self.topics_started)

    def has_budget_for_topic(self) -> bool:
        if self.topics_started >= self.max_backlog_topics:
            return False
        if self.remaining_sources() < 1 and self.remaining_model_calls() < 1:
            return False
        return True

    def consume_sources(self, n: int):
        self.sources_used += n

    def consume_model_calls(self, n: int):
        self.model_calls_used += n

    def consume_screenshots(self, n: int):
        self.screenshots_used += n

    def topic_source_cap(self) -> int:
        return min(self.per_topic_max_sources, self.remaining_sources())

    def topic_model_call_cap(self) -> int:
        return min(self.per_topic_max_model_calls, self.remaining_model_calls())

    def topic_screenshot_cap(self) -> int:
        return min(self.per_topic_max_screenshots, self.remaining_screenshots())

    def to_dict(self) -> dict:
        return {
            "max_total_sources": self.max_total_sources,
            "max_total_model_calls": self.max_total_model_calls,
            "max_total_screenshots": self.max_total_screenshots,
            "max_backlog_topics": self.max_backlog_topics,
            "per_topic_max_sources": self.per_topic_max_sources,
            "per_topic_max_model_calls": self.per_topic_max_model_calls,
            "per_topic_max_screenshots": self.per_topic_max_screenshots,
            "reserve_final_report_budget": self.reserve_final_report_budget,
            "sources_used": self.sources_used,
            "model_calls_used": self.model_calls_used,
            "screenshots_used": self.screenshots_used,
            "topics_started": self.topics_started,
            "topics_completed": self.topics_completed,
            "remaining_sources": self.remaining_sources(),
            "remaining_model_calls": self.remaining_model_calls(),
            "remaining_screenshots": self.remaining_screenshots(),
            "remaining_topics": self.remaining_topics(),
        }

    def snapshot(self) -> dict:
        return {
            "sources_used": self.sources_used,
            "model_calls_used": self.model_calls_used,
            "screenshots_used": self.screenshots_used,
            "topics_started": self.topics_started,
            "topics_completed": self.topics_completed,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
