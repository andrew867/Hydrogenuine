"""Persistent daemon run state — on-disk JSON files in the state directory."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class RunState:
    run_id: str = ""
    started_at: str = ""
    status: str = "starting"  # starting / running / stopped / panicked / completed / failed
    cycle_count: int = 0
    receipt_count: int = 0
    checkin_count: int = 0
    checkpoint_count: int = 0
    boundary_scan_count: int = 0
    seeds_worked: list[str] = field(default_factory=list)
    seeds_skipped: list[str] = field(default_factory=list)
    current_seed_id: str = ""
    current_task_id: str = ""
    current_model: str = ""
    current_science_mode: str = ""
    verdict_so_far: str = "YELLOW_IN_PROGRESS"
    elapsed_seconds: float = 0.0
    fatal_error: str = ""
    boundary_violations: int = 0
    last_checkin_hour: int = -1
    last_checkpoint_minute: int = -1
    last_boundary_scan_minute: int = -1
    output_classifications: dict = field(default_factory=lambda: {
        "normal_content": 0, "content_plus_reasoning": 0, "reasoning_only": 0,
        "reasoning_only_truncated": 0, "empty_content": 0, "truncated_content": 0,
        "timeout": 0, "client_disconnect": 0, "tool_call_shaped": 0,
        "final_answer_retry_success": 0, "final_answer_retry_failed": 0,
        "forbidden_model_attempt": 0, "remote_fallback_attempt": 0,
        "malformed_response": 0,
    })
    retry_attempts: int = 0
    retry_successes: int = 0
    retry_failures: int = 0
    autopilot_proposals: int = 0
    autopilot_decisions: int = 0
    autopilot_approvals: int = 0
    autopilot_denials: int = 0
    knowledge_candidates: int = 0
    knowledge_promotions: int = 0
    evidence_gaps: int = 0
    uncertainty_records: int = 0


def state_path(state_dir: str | Path) -> Path:
    return Path(state_dir) / "state.json"


def save_state(s: RunState, state_dir: str | Path) -> None:
    p = state_path(state_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(asdict(s), indent=2, default=str), encoding="utf-8")


def load_state(state_dir: str | Path) -> RunState | None:
    p = state_path(state_dir)
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    s = RunState()
    for k, v in d.items():
        if hasattr(s, k):
            setattr(s, k, v)
    return s
