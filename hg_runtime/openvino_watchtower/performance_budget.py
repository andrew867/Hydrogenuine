"""Performance budget evaluation — slow is not failure; timeout is RED."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

WORKSPACE = Path(__file__).resolve().parents[2]
DEFAULT_BUDGET_PATH = WORKSPACE / "configs/openvino_watchtower/performance_budget.json"

PerfVerdict = Literal[
    "PERF_GREEN",
    "PERF_YELLOW_SLOW",
    "PERF_RED_TIMEOUT",
    "PERF_STALE",
    "PERF_CONTACT_LOST",
]


@dataclass
class PerformanceBudget:
    warning_first_token_ms: float = 5000
    red_first_token_ms: float = 15000
    warning_total_inference_ms: float = 30000
    red_total_inference_ms: float = 120000
    warning_snapshot_age_seconds: float = 10
    red_snapshot_age_seconds: float = 60
    contact_lost_seconds: float = 300

    @classmethod
    def load(cls, path: Path | None = None) -> PerformanceBudget:
        p = path or DEFAULT_BUDGET_PATH
        if not p.is_file():
            return cls()
        data = json.loads(p.read_text(encoding="utf-8"))
        return cls(**{k: data[k] for k in cls.__dataclass_fields__ if k in data})

    def to_dict(self) -> dict[str, Any]:
        return {
            "warning_first_token_ms": self.warning_first_token_ms,
            "red_first_token_ms": self.red_first_token_ms,
            "warning_total_inference_ms": self.warning_total_inference_ms,
            "red_total_inference_ms": self.red_total_inference_ms,
            "warning_snapshot_age_seconds": self.warning_snapshot_age_seconds,
            "red_snapshot_age_seconds": self.red_snapshot_age_seconds,
            "contact_lost_seconds": self.contact_lost_seconds,
        }


def evaluate_span(span: dict[str, Any], budget: PerformanceBudget | None = None) -> str:
    budget = budget or PerformanceBudget.load()
    duration = float(span.get("duration_ms") or 0)
    first_token = float(span.get("first_token_ms") or duration)
    if span.get("status") == "failed" and span.get("error", "").lower().find("timeout") >= 0:
        return "PERF_RED_TIMEOUT"
    if duration >= budget.red_total_inference_ms or first_token >= budget.red_first_token_ms:
        return "PERF_RED_TIMEOUT"
    if duration >= budget.warning_total_inference_ms or first_token >= budget.warning_first_token_ms:
        return "PERF_YELLOW_SLOW"
    return "PERF_GREEN"


def evaluate_snapshot(snapshot: dict[str, Any], budget: PerformanceBudget | None = None) -> dict[str, Any]:
    budget = budget or PerformanceBudget.load()
    freshness = str(snapshot.get("freshness_verdict", "fresh"))
    age_ms = float(snapshot.get("freshness_age_ms") or 0)
    age_s = age_ms / 1000.0

    if freshness == "contact_lost" or age_s >= budget.contact_lost_seconds:
        verdict: PerfVerdict = "PERF_CONTACT_LOST"
    elif freshness == "stale" or age_s >= budget.red_snapshot_age_seconds:
        verdict = "PERF_STALE"
    elif age_s >= budget.warning_snapshot_age_seconds:
        verdict = "PERF_YELLOW_SLOW"
    else:
        verdict = "PERF_GREEN"

    span_verdicts = []
    for span in (snapshot.get("recent_inference_spans") or [])[:5]:
        span_verdicts.append({"span_id": span.get("span_id"), "verdict": evaluate_span(span, budget)})

    overall = verdict
    for sv in span_verdicts:
        if sv["verdict"] == "PERF_RED_TIMEOUT":
            overall = "PERF_RED_TIMEOUT"
            break
        if sv["verdict"] == "PERF_YELLOW_SLOW" and overall == "PERF_GREEN":
            overall = "PERF_YELLOW_SLOW"

    return {
        "verdict": overall,
        "snapshot_freshness_verdict": freshness,
        "span_verdicts": span_verdicts,
        "budget": budget.to_dict(),
        "authority_created": False,
        "permission_granted": False,
    }


__all__ = ["PerformanceBudget", "PerfVerdict", "evaluate_snapshot", "evaluate_span"]
