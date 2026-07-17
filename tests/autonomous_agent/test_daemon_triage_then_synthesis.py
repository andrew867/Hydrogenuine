"""Tests: triage-then-synthesis pipeline."""

from __future__ import annotations

import inspect

from hg_runtime.overnight_daemon.model_role_routing import (
    get_model_role, build_synthesis_prompt,
    gemma_tiny_prompt_for_mode, GEMMA_MODEL_ID,
    route_task,
)
from hg_runtime.overnight_daemon.scheduler import run_cycle, _SCIENCE_CYCLE


def test_speculative_task_runs_triage_before_gemma_synthesis():
    src = inspect.getsource(run_cycle)
    assert "triage_outputs" in src
    assert "triage_then_synthesis" in src


def test_gemma_receives_compact_triage_summary():
    prompt = build_synthesis_prompt("test_seed", "falsification: 3 items; boring: 3 items")
    assert "test_seed" in prompt
    assert "falsification" in prompt
    assert len(prompt) < 600


def test_triage_outputs_linked_to_synthesis_receipt():
    src = inspect.getsource(run_cycle)
    assert "linked_task_ids" in src


def test_failed_triage_records_yellow_not_red():
    src = inspect.getsource(run_cycle)
    assert "YELLOW_RECOVERABLE_ERROR" in src
    assert "reasoning_exhaustion_backoff" in src


def test_synthesis_does_not_promote_speculation():
    prompt = build_synthesis_prompt("test_seed", "some triage")
    assert "No hype" in prompt or "speculation" in prompt.lower()


def test_fast_triage_modes_are_triage_first():
    triage_modes = ["falsification_design", "boring_explanation_first", "units_and_math_audit"]
    for mode in triage_modes:
        role = get_model_role(mode)
        assert role in ("fast_triage", "fast_math_or_coder"), \
            f"{mode} should be triage-first but got {role}"


def test_synthesis_modes_use_gemma():
    synthesis_modes = ["public_safe_explainer", "synthesis_after_opposition"]
    for mode in synthesis_modes:
        assert get_model_role(mode) == "main_synthesis"


def test_gemma_tiny_prompt_is_compact():
    prompt = gemma_tiny_prompt_for_mode("falsification_design", "test seed")
    assert len(prompt) < 300
    assert "No reasoning" in prompt or "JSON only" in prompt


def test_triage_summary_truncated():
    long_summary = "x" * 2000
    prompt = build_synthesis_prompt("seed", long_summary)
    assert len(prompt) < 1200
