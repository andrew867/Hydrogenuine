"""Tests for profile memory isolation / no parallel lifetime."""

from __future__ import annotations

import pytest

APPLIED = "2026-06-23T00:00:00Z"


def _assignment(task_id="iso"):
    from hg_runtime.cognitive_profile_overlay.profile_loader import load_all_profiles
    from hg_runtime.cognitive_profile_overlay.overlay_assignment import assign_profile
    pid = load_all_profiles()[0].profile_id
    return assign_profile(task_id=task_id, profile_id=pid,
                          assignment_scope="audit", applied_at=APPLIED)


def test_profile_output_namespace_isolated():
    from hg_runtime.cognitive_profile_overlay.memory_isolation import namespace_is_isolated
    a = _assignment()
    assert namespace_is_isolated(a) is True


def test_profile_cannot_write_agent_identity_memory():
    from hg_runtime.cognitive_profile_overlay.memory_isolation import can_write_identity_memory
    a = _assignment()
    assert can_write_identity_memory(a) is False


def test_profile_cannot_create_parallel_lifetime():
    a = _assignment()
    assert a.creates_parallel_lifetime is False


def test_profile_cannot_self_extend_assignment():
    from hg_runtime.cognitive_profile_overlay.memory_isolation import audit_isolation
    a = _assignment()
    audit = audit_isolation(a)
    assert audit.can_self_extend is False


def test_profile_cannot_modify_stop_panic():
    from hg_runtime.cognitive_profile_overlay.memory_isolation import audit_isolation
    a = _assignment()
    audit = audit_isolation(a)
    assert "profile_cannot_modify_stop_panic" in audit.invariants_held


def test_profile_cannot_mark_phase19_green():
    from hg_runtime.cognitive_profile_overlay.memory_isolation import audit_isolation
    a = _assignment()
    audit = audit_isolation(a)
    assert "profile_cannot_mark_phase19_green" in audit.invariants_held


def test_profile_cannot_mark_phase24_green():
    from hg_runtime.cognitive_profile_overlay.memory_isolation import audit_isolation
    a = _assignment()
    audit = audit_isolation(a)
    assert "profile_cannot_mark_phase24_green" in audit.invariants_held


def test_isolation_passes_for_clean_assignment():
    from hg_runtime.cognitive_profile_overlay.memory_isolation import isolation_passes
    a = _assignment()
    assert isolation_passes(a) is True


def test_isolation_fails_if_identity_memory_write():
    from hg_runtime.cognitive_profile_overlay.memory_isolation import audit_isolation
    a = _assignment()
    a.writes_to_agent_identity_memory = True
    audit = audit_isolation(a)
    assert len(audit.violations) > 0


def test_all_invariants_present():
    from hg_runtime.cognitive_profile_overlay.memory_isolation import all_invariants
    invs = all_invariants()
    assert "profile_is_not_identity" in invs
    assert "profile_cannot_write_identity_memory" in invs
    assert len(invs) >= 14
