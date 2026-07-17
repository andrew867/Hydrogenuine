"""Tests for temporary profile assignment."""

from __future__ import annotations

import pytest

APPLIED = "2026-06-23T00:00:00Z"


def _first_profile_id():
    from hg_runtime.cognitive_profile_overlay.profile_loader import load_all_profiles
    return load_all_profiles()[0].profile_id


def test_creates_temporary_profile_assignment():
    from hg_runtime.cognitive_profile_overlay.overlay_assignment import assign_profile
    a = assign_profile(task_id="t1", profile_id=_first_profile_id(),
                       assignment_scope="research", applied_at=APPLIED)
    assert a is not None
    assert a.temporary is True
    assert a.receipt_hash


def test_profile_assignment_has_expiration_or_max_turns():
    from hg_runtime.cognitive_profile_overlay.overlay_assignment import (
        assign_profile, assignment_is_bounded,
    )
    a = assign_profile(task_id="t2", profile_id=_first_profile_id(),
                       assignment_scope="audit", applied_at=APPLIED)
    assert assignment_is_bounded(a)


def test_profile_assignment_is_not_identity():
    from hg_runtime.cognitive_profile_overlay.overlay_assignment import assign_profile
    a = assign_profile(task_id="t3", profile_id=_first_profile_id(),
                       assignment_scope="QA", applied_at=APPLIED)
    assert a.profile_is_identity is False
    assert a.creates_parallel_lifetime is False


def test_profile_assignment_grants_no_authority():
    from hg_runtime.cognitive_profile_overlay.overlay_assignment import assign_profile
    a = assign_profile(task_id="t4", profile_id=_first_profile_id(),
                       assignment_scope="writing", applied_at=APPLIED)
    assert a.authority_granted is False


def test_profile_assignment_authorizes_no_tools():
    from hg_runtime.cognitive_profile_overlay.overlay_assignment import assign_profile
    a = assign_profile(task_id="t5", profile_id=_first_profile_id(),
                       assignment_scope="research", applied_at=APPLIED)
    assert a.tools_authorized is False


def test_profile_assignment_creates_no_live_effects():
    from hg_runtime.cognitive_profile_overlay.overlay_assignment import assign_profile
    a = assign_profile(task_id="t6", profile_id=_first_profile_id(),
                       assignment_scope="research", applied_at=APPLIED)
    assert a.live_effects_authorized is False


def test_profile_assignment_requires_operator_review():
    from hg_runtime.cognitive_profile_overlay.overlay_assignment import assign_profile
    a = assign_profile(task_id="t7", profile_id=_first_profile_id(),
                       assignment_scope="proof_review", applied_at=APPLIED)
    assert a.operator_review_required is True


def test_assignment_is_safe():
    from hg_runtime.cognitive_profile_overlay.overlay_assignment import (
        assign_profile, assignment_is_safe,
    )
    a = assign_profile(task_id="t8", profile_id=_first_profile_id(),
                       assignment_scope="audit", applied_at=APPLIED)
    safe, violations = assignment_is_safe(a)
    assert safe, violations


def test_profile_cannot_self_extend():
    from hg_runtime.cognitive_profile_overlay.overlay_assignment import (
        assign_profile, attempt_self_extend,
    )
    a = assign_profile(task_id="t9", profile_id=_first_profile_id(),
                       assignment_scope="audit", applied_at=APPLIED)
    assert attempt_self_extend(a) is False


def test_missing_profile_returns_none():
    from hg_runtime.cognitive_profile_overlay.overlay_assignment import assign_profile
    a = assign_profile(task_id="t10", profile_id="nope",
                       assignment_scope="audit", applied_at=APPLIED)
    assert a is None
