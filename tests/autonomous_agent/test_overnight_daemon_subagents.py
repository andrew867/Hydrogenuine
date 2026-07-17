"""Tests: subagent task workers — bounded, no authority, no identity."""

from __future__ import annotations

import pytest

from hg_runtime.overnight_daemon.subagents import (
    SUBAGENT_ROLES, create_task, task_grants_authority, task_authorizes_tools,
    task_creates_live_effects, task_is_identity, task_is_parallel_lifetime,
    task_can_self_authorize, WorkerPool, SubagentTask,
)


def test_subagent_roles_registered():
    assert len(SUBAGENT_ROLES) >= 9
    required = {"seed_ranker", "falsification_worker", "boring_explanation_worker",
                "units_math_audit_worker", "bridge_theory_worker",
                "public_safe_explainer_worker", "proof_auditor_worker",
                "checkin_writer_worker", "final_report_worker"}
    assert required.issubset(set(SUBAGENT_ROLES))


def test_subagent_is_task_worker_not_identity():
    task = create_task("falsification_worker", "test_seed")
    assert not task_is_identity(task)
    assert task.role == "falsification_worker"


def test_subagent_grants_no_authority():
    for role in SUBAGENT_ROLES:
        task = create_task(role, "test_seed")
        assert not task_grants_authority(task), f"{role} grants authority"
        assert task.authority_granted is False


def test_subagent_authorizes_no_tools():
    for role in SUBAGENT_ROLES:
        task = create_task(role, "test_seed")
        assert not task_authorizes_tools(task), f"{role} authorizes tools"
        assert task.tools_authorized is False


def test_subagent_creates_no_live_effects():
    for role in SUBAGENT_ROLES:
        task = create_task(role, "test_seed")
        assert not task_creates_live_effects(task), f"{role} creates live effects"
        assert task.live_effects_created is False


def test_subagent_cannot_self_authorize():
    for role in SUBAGENT_ROLES:
        task = create_task(role, "test_seed")
        assert not task_can_self_authorize(task)


def test_subagent_not_parallel_lifetime():
    for role in SUBAGENT_ROLES:
        task = create_task(role, "test_seed")
        assert not task_is_parallel_lifetime(task)


def test_max_concurrent_subagents_enforced():
    pool = WorkerPool(max_concurrent=1)
    t1 = create_task("falsification_worker", "seed1")
    t2 = create_task("boring_explanation_worker", "seed2")
    assert pool.can_enqueue()
    pool.enqueue(t1)
    assert not pool.can_enqueue()
    assert not pool.enqueue(t2)


def test_subagent_task_writes_receipt():
    task = create_task("falsification_worker", "test_seed")
    assert task.receipt_hash == ""
    task.receipt_hash = "abc123"
    assert task.receipt_hash == "abc123"


def test_subagent_failure_recorded_not_hidden():
    pool = WorkerPool(max_concurrent=1)
    task = create_task("falsification_worker", "test_seed")
    pool.enqueue(task)
    pool.finish(task, success=False)
    assert task.status == "failed"
    assert task in pool.failed
    assert len(pool.failed) == 1


def test_subagent_task_fields():
    task = create_task("seed_ranker", "test_seed", input_summary="ranking seeds")
    assert task.role == "seed_ranker"
    assert task.seed_id == "test_seed"
    assert task.input_summary == "ranking seeds"
    assert task.authority_granted is False
    assert task.tools_authorized is False
    assert task.live_effects_created is False


def test_unknown_role_rejected():
    with pytest.raises(ValueError, match="unknown subagent role"):
        create_task("hacker_worker", "test_seed")
