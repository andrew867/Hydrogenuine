"""Long-soak telemetry tracking.

Tracks wall-clock, cycles, sources, model calls, screenshots, budget use,
and soak progress. Telemetry is observation, not authority. No promotion.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class SoakTelemetry:
    run_id: str = ""
    _start: float = 0.0
    _events: list[dict] = field(default_factory=list)

    cycle_count: int = 0
    sources_attempted: int = 0
    sources_succeeded: int = 0
    sources_failed: int = 0
    screenshots_attempted: int = 0
    screenshots_succeeded: int = 0
    screenshots_failed: int = 0
    model_calls_planned: int = 0
    model_calls_started: int = 0
    model_calls_succeeded: int = 0
    model_calls_timed_out: int = 0
    model_calls_skipped: int = 0
    model_seconds: float = 0.0
    compression_count: int = 0
    useful_outputs: int = 0
    external_effects: int = 0
    promotions: int = 0
    stop_panic_seen: bool = False

    backlog_topics_started: int = 0
    backlog_topics_completed: int = 0

    def start(self, run_id: str):
        self.run_id = run_id
        self._start = time.monotonic()
        self._emit("run_started")

    def elapsed(self) -> float:
        if self._start == 0:
            return 0.0
        return time.monotonic() - self._start

    def record_source_attempt(self, success: bool):
        self.sources_attempted += 1
        if success:
            self.sources_succeeded += 1
            self._emit("source_completed")
        else:
            self.sources_failed += 1
            self._emit("source_failed")

    def record_model_call(self, *, status: str, elapsed_s: float,
                          output_chars: int = 0):
        self.model_calls_started += 1
        self.model_seconds += elapsed_s
        if status == "succeeded":
            self.model_calls_succeeded += 1
            if output_chars > 0:
                self.useful_outputs += 1
        elif status == "timed_out":
            self.model_calls_timed_out += 1
        elif status == "skipped":
            self.model_calls_skipped += 1
        self._emit(f"model_call_{status}")

    def record_backlog_topic(self, completed: bool):
        self.backlog_topics_started += 1
        if completed:
            self.backlog_topics_completed += 1
            self._emit("backlog_topic_completed")
        else:
            self._emit("backlog_topic_started")

    def record_stop_panic(self):
        self.stop_panic_seen = True
        self._emit("stop_panic_seen")

    def record_checkpoint(self):
        self._emit("checkpoint_written")

    def finalize(self):
        self._emit("run_finalized")

    def summary(self) -> dict:
        return {
            "run_id": self.run_id,
            "elapsed_seconds": round(self.elapsed(), 2),
            "cycle_count": self.cycle_count,
            "sources_attempted": self.sources_attempted,
            "sources_succeeded": self.sources_succeeded,
            "sources_failed": self.sources_failed,
            "screenshots_attempted": self.screenshots_attempted,
            "screenshots_succeeded": self.screenshots_succeeded,
            "screenshots_failed": self.screenshots_failed,
            "model_calls_planned": self.model_calls_planned,
            "model_calls_started": self.model_calls_started,
            "model_calls_succeeded": self.model_calls_succeeded,
            "model_calls_timed_out": self.model_calls_timed_out,
            "model_calls_skipped": self.model_calls_skipped,
            "model_seconds": round(self.model_seconds, 2),
            "useful_outputs": self.useful_outputs,
            "compression_count": self.compression_count,
            "external_effects": self.external_effects,
            "promotions": self.promotions,
            "stop_panic_seen": self.stop_panic_seen,
            "backlog_topics_started": self.backlog_topics_started,
            "backlog_topics_completed": self.backlog_topics_completed,
            "telemetry_is_observation_not_authority": True,
            "promotion_allowed": False,
            "operator_review_required": True,
        }

    def write(self, out_dir: str):
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "telemetry_summary.json"), "w",
                  encoding="utf-8") as f:
            json.dump(self.summary(), f, indent=2)

        with open(os.path.join(out_dir, "telemetry_receipts.jsonl"), "w",
                  encoding="utf-8") as f:
            for ev in self._events:
                f.write(json.dumps(ev) + "\n")

    def _emit(self, event_type: str):
        self._events.append({
            "schema_version": "telemetry_event_v1",
            "event_type": event_type,
            "run_id": self.run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "elapsed_s": round(self.elapsed(), 3),
        })
