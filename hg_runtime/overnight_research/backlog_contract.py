"""Backlog topic contract and validation.

No promotion. Operator review required.
Research backlog priority is not truth priority.
Backlog completion is not knowledge promotion.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from hg_runtime.overnight_research.question_contract import RISK_MODES

try:
    from hg_runtime.source_grounding.read_only_web_retriever import is_url_safe_for_read
except ImportError:
    def is_url_safe_for_read(url: str) -> tuple[bool, str]:
        if any(x in url for x in ["127.0.0.1", "localhost", "192.168.", "10.", "172.16."]):
            return False, "private/internal URL"
        return True, ""

TOPIC_STATES = (
    "queued", "running", "complete", "partial_yellow",
    "blocked", "skipped_budget_exhausted", "skipped_risk_policy",
    "skipped_missing_source", "skipped_operator_review_required",
)


@dataclass
class BacklogTopic:
    topic_id: str
    title: str
    question: str
    risk_mode: str = "normal"
    priority: int = 100
    source_urls: list[str] = field(default_factory=list)
    seed_id: str = ""
    tags: list[str] = field(default_factory=list)
    max_sources: int | None = None
    max_model_calls: int | None = None
    max_screenshots: int | None = None
    operator_review_required: bool = True
    promotion_allowed: bool = False

    def validate(self) -> list[str]:
        errors = []
        if not self.topic_id or not self.topic_id.strip():
            errors.append("topic_id is required")
        if not self.question or not self.question.strip():
            errors.append("question is required")
        if self.risk_mode not in RISK_MODES:
            errors.append(f"risk_mode must be one of {RISK_MODES}")
        if self.promotion_allowed:
            errors.append("promotion_allowed must be false")
        if not self.operator_review_required:
            errors.append("operator_review_required must be true")
        for url in self.source_urls:
            safe, reason = is_url_safe_for_read(url)
            if not safe:
                errors.append(f"unsafe URL rejected: {url} ({reason})")
        return errors

    def to_dict(self) -> dict:
        return {
            "topic_id": self.topic_id,
            "title": self.title,
            "question": self.question,
            "risk_mode": self.risk_mode,
            "priority": self.priority,
            "source_urls": self.source_urls,
            "seed_id": self.seed_id,
            "tags": self.tags,
            "max_sources": self.max_sources,
            "max_model_calls": self.max_model_calls,
            "max_screenshots": self.max_screenshots,
            "operator_review_required": self.operator_review_required,
            "promotion_allowed": self.promotion_allowed,
        }


def load_backlog_file(path: str) -> tuple[list[BacklogTopic], list[dict]]:
    topics = []
    skip_receipts = []

    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()

    if content.startswith("["):
        entries = json.loads(content)
    else:
        entries = [json.loads(line) for line in content.strip().split("\n") if line.strip()]

    for entry in entries:
        topic = BacklogTopic(
            topic_id=entry.get("topic_id", ""),
            title=entry.get("title", ""),
            question=entry.get("question", ""),
            risk_mode=entry.get("risk_mode", "normal"),
            priority=entry.get("priority", 100),
            source_urls=entry.get("source_urls", []),
            seed_id=entry.get("seed_id", ""),
            tags=entry.get("tags", []),
            max_sources=entry.get("max_sources"),
            max_model_calls=entry.get("max_model_calls"),
            max_screenshots=entry.get("max_screenshots"),
            operator_review_required=entry.get("operator_review_required", True),
            promotion_allowed=entry.get("promotion_allowed", False),
        )
        errors = topic.validate()
        if errors:
            skip_receipts.append({
                "topic_id": topic.topic_id or "(missing)",
                "event_type": "topic_skipped",
                "skip_reason": "validation_error",
                "errors": errors,
                "promotion_allowed": False,
                "operator_review_required": True,
            })
        else:
            topics.append(topic)

    topics.sort(key=lambda t: t.priority)
    return topics, skip_receipts


def filter_by_risk_ceiling(topics: list[BacklogTopic], ceiling: str) -> tuple[list[BacklogTopic], list[dict]]:
    risk_order = {"normal": 0, "speculative": 1, "high_risk_speculative": 2}
    ceiling_level = risk_order.get(ceiling, 0)
    passed = []
    skipped = []
    for t in topics:
        t_level = risk_order.get(t.risk_mode, 0)
        if t_level > ceiling_level:
            skipped.append({
                "topic_id": t.topic_id,
                "event_type": "topic_skipped",
                "skip_reason": "skipped_risk_policy",
                "topic_risk": t.risk_mode,
                "ceiling": ceiling,
                "promotion_allowed": False,
                "operator_review_required": True,
            })
        else:
            passed.append(t)
    return passed, skipped
