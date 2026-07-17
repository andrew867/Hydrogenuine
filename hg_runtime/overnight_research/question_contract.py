"""Research question input contract and validation.

No promotion. No external effects. Operator review required.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


RISK_MODES = ("normal", "speculative", "high_risk_speculative")


@dataclass
class ResearchQuestion:
    question: str
    run_label: str = ""
    seed_id: str = ""
    source_urls: list[str] = field(default_factory=list)
    topic_tags: list[str] = field(default_factory=list)
    risk_mode: str = "normal"
    max_sources: int = 6
    max_screenshots: int = 3
    max_model_calls: int = 12
    model_endpoint: str = "http://127.0.0.1:1234/v1"
    model_name: str = "qwen2.5-0.5b-instruct"
    model_timeout_seconds: int = 120
    model_max_output_tokens: int = 900
    max_source_chars_for_model: int = 6000
    live_http_get: bool = False
    http_user_agent_preset: str = "chrome"
    enable_screenshots: bool = False
    model_profile: str = "normal_fast"
    enable_source_chunking: bool = True
    wall_clock_budget_seconds: float = 600.0
    reserve_final_report_seconds: float = 30.0
    per_topic_wall_clock_seconds: float = 180.0
    no_remote_model_fallback: bool = True
    no_knowledge_promotion: bool = True
    operator_review_required: bool = True
    output_root: str = ""
    dry_run: bool = False

    def validate(self) -> list[str]:
        errors = []
        if not self.question or not self.question.strip():
            errors.append("question is required")
        if self.risk_mode not in RISK_MODES:
            errors.append(f"risk_mode must be one of {RISK_MODES}")
        if self.max_sources < 0:
            errors.append("max_sources must be >= 0")
        if self.max_model_calls < 0:
            errors.append("max_model_calls must be >= 0")
        if not self.no_knowledge_promotion:
            errors.append("knowledge promotion must remain disabled")
        if not self.operator_review_required:
            errors.append("operator review must remain required")
        if self.model_profile not in ("tiny_fast", "normal_fast", "deep"):
            errors.append(f"model_profile must be tiny_fast, normal_fast, or deep")
        return errors

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "run_label": self.run_label,
            "seed_id": self.seed_id,
            "source_urls": self.source_urls,
            "topic_tags": self.topic_tags,
            "risk_mode": self.risk_mode,
            "max_sources": self.max_sources,
            "max_screenshots": self.max_screenshots,
            "max_model_calls": self.max_model_calls,
            "model_endpoint": self.model_endpoint,
            "model_name": self.model_name,
            "model_timeout_seconds": self.model_timeout_seconds,
            "model_max_output_tokens": self.model_max_output_tokens,
            "max_source_chars_for_model": self.max_source_chars_for_model,
            "live_http_get": self.live_http_get,
            "enable_screenshots": self.enable_screenshots,
            "no_remote_model_fallback": self.no_remote_model_fallback,
            "model_profile": self.model_profile,
            "enable_source_chunking": self.enable_source_chunking,
            "wall_clock_budget_seconds": self.wall_clock_budget_seconds,
            "reserve_final_report_seconds": self.reserve_final_report_seconds,
            "no_knowledge_promotion": self.no_knowledge_promotion,
            "operator_review_required": self.operator_review_required,
            "dry_run": self.dry_run,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
