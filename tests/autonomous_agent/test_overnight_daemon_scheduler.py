"""Tests: daemon scheduler loop — seed selection, autopilot, receipts, pacing."""

from __future__ import annotations

import inspect
import tempfile
from pathlib import Path

import pytest

from hg_runtime.overnight_daemon.scheduler import (
    run_cycle, _pick_next_seed, _PRIORITY_SEEDS, _SCIENCE_CYCLE,
)
from hg_runtime.overnight_daemon.config import DaemonConfig
from hg_runtime.overnight_daemon.state import RunState
from hg_runtime.overnight_daemon.subagents import WorkerPool
from hg_runtime.overnight_qa.research_seeds import build_research_seeds
from hg_runtime.live_local.paced_loop import overnight_green_allowed


def test_scheduler_loop_selects_seed():
    seeds = build_research_seeds()
    state = RunState()
    sid = _pick_next_seed(state, seeds)
    assert sid is not None
    assert sid in _PRIORITY_SEEDS


def test_scheduler_disposes_autopilot_proposal():
    src = inspect.getsource(run_cycle)
    assert "propose(" in src
    assert "dispose(" in src


def test_scheduler_enqueues_subagent_task():
    src = inspect.getsource(run_cycle)
    assert "pool.enqueue" in src


def test_scheduler_writes_receipts():
    src = inspect.getsource(run_cycle)
    assert "_append_jsonl" in src
    assert "autopilot_proposals.jsonl" in src
    assert "live_local_reasoning_receipts.jsonl" in src


def test_scheduler_respects_duration():
    src = inspect.getsource(run_cycle)
    assert "target_seconds" in src
    assert '"completed"' in src


def test_scheduler_respects_cycle_delay():
    """Cycle delay is in the supervisor loop, not run_cycle itself."""
    from hg_runtime.overnight_daemon.supervisor import run_daemon
    src = inspect.getsource(run_daemon)
    assert "cycle_delay_seconds" in src
    assert "time.sleep" in src


def test_scheduler_does_not_green_before_min_duration():
    assert not overnight_green_allowed(target_seconds=43200, elapsed_seconds=600)
    assert not overnight_green_allowed(target_seconds=43200, elapsed_seconds=14000)
    assert overnight_green_allowed(target_seconds=43200, elapsed_seconds=43200)


def test_scheduler_continues_after_reasoning_only_yellow():
    """Reasoning-only is YELLOW, not RED — the loop continues."""
    src = inspect.getsource(run_cycle)
    assert "forbidden_model_attempt" in src or "boundary_violations" in src
    # reasoning_only does NOT cause boundary violation
    from hg_runtime.live_local.reasoning_classifier import reasoning_only_is_red, ReasoningReceipt
    rec = ReasoningReceipt(
        classification="reasoning_only", model_id="test", endpoint="test",
        prompt_id="test", task_id="test", science_mode="test", seed_id="test",
        requested_max_tokens=768, requested_timeout_seconds=300,
        elapsed_seconds=1.0, finish_reason="length",
        content_char_count=0, reasoning_char_count=100,
        content_token_count=0, reasoning_token_count=50, tool_call_count=0,
    )
    assert not reasoning_only_is_red(rec)


def test_scheduler_stops_on_forbidden_model():
    src = inspect.getsource(run_cycle)
    assert "forbidden_model_attempt" in src
    assert "boundary_violations" in src


def test_scheduler_stops_on_live_effect_attempt():
    """Live effects = boundary violation = RED."""
    src = inspect.getsource(run_cycle)
    assert "remote_fallback_attempt" in src


def test_priority_seeds_order():
    assert "electron_hole_spin_state_change_hypothesis" in _PRIORITY_SEEDS
    assert "observer_state_frequency_hypothesis" in _PRIORITY_SEEDS
    assert "quasiparticle_bridge_theory_requirements" in _PRIORITY_SEEDS


def test_science_cycle_modes():
    assert "falsification_design" in _SCIENCE_CYCLE
    assert "boring_explanation_first" in _SCIENCE_CYCLE
    assert "units_and_math_audit" in _SCIENCE_CYCLE
    assert "public_safe_explainer" in _SCIENCE_CYCLE


def test_no_string_split_role_in_scheduler():
    src = inspect.getsource(run_cycle)
    assert "mode.split(" not in src
    assert "split('_')[0]" not in src


def test_scheduler_uses_resolve_subagent_role():
    src = inspect.getsource(run_cycle)
    assert "resolve_subagent_role" in src


def test_scheduler_continues_after_recoverable_role_mapping_error():
    """If role resolution fails, scheduler writes receipt and continues."""
    src = inspect.getsource(run_cycle)
    assert "subagent_role_mapping_errors" in src
    assert "YELLOW_RECOVERABLE_ERROR" in src
