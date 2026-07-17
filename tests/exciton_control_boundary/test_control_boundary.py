"""EXCITON Phase 0 — control boundary tests. No control grants authority."""

from __future__ import annotations

import pytest

from hg_runtime.exciton.control_boundary import ExcitonControlBoundary
from hg_runtime.exciton.schema import (
    ExcitonControlDecisionKind,
    ExcitonControlKind,
    ExcitonControlRequest,
    new_id,
)

B = ExcitonControlBoundary()
D = ExcitonControlDecisionKind
K = ExcitonControlKind


def _decide(kind: ExcitonControlKind):
    return B.decide(ExcitonControlRequest(new_id("req"), kind))


ALLOWED_CASES = [
    (K.REFRESH_STATUS, D.ALLOW_READ_ONLY),
    (K.OPEN_PROOF_LINK, D.ALLOW_READ_ONLY),
    (K.COPY_SAFE_SUMMARY, D.ALLOW_READ_ONLY),
    (K.REQUEST_SELF_MIRROR_QUERY, D.ALLOW_READ_ONLY),
    (K.REQUEST_PROOF_RECHECK, D.ALLOW_READ_ONLY),
    (K.RUN_DRY_RUN_GATE, D.ALLOW_READ_ONLY),
    (K.ADD_OPERATOR_NOTE, D.ALLOW_DRAFT_ONLY),
    (K.REQUEST_ANCHOR_QUEUE_REVIEW, D.QUEUE_FOR_OPERATOR),
    (K.STOP_AGENT, D.FULL_STOP),
    (K.PANIC_STOP, D.FULL_STOP),
]

DENIED = [
    K.PUBLISH_SOCIAL, K.SEND_EMAIL, K.CREATE_ACCOUNT, K.LOGIN_FORM_SUBMIT,
    K.MUTATE_MEMORY, K.MUTATE_SOURCE, K.PUSH_GITHUB_ANCHOR, K.DELETE_PROOF_BUNDLE,
    K.START_OEA, K.START_TER, K.APPLY_SRP, K.ENABLE_LIVE_MIC, K.ENABLE_PLAYBACK,
    K.START_SOAK, K.START_AUTONOMOUS_LOOP,
]


@pytest.mark.parametrize("kind,expected", ALLOWED_CASES)
def test_allowed_controls_resolve_correctly(kind, expected):
    assert _decide(kind).decision == expected


@pytest.mark.parametrize("kind", DENIED)
def test_forbidden_controls_denied(kind):
    assert _decide(kind).decision == D.DENY


def test_stop_and_panic_full_stop():
    assert _decide(K.STOP_AGENT).decision == D.FULL_STOP
    assert _decide(K.PANIC_STOP).decision == D.FULL_STOP


def test_no_decision_grants_permission_or_authority():
    for kind in list(K):
        payload = _decide(kind).to_payload()
        assert payload["permission_granted"] is False
        assert payload["authority_created"] is False
        assert payload["advisory_only"] is True


def test_default_deny_for_unknown_control_via_forbidden_check():
    # Every kind is either an allowed decision or forbidden; nothing falls through to ALLOW.
    for kind in DENIED:
        assert B.is_forbidden(kind) is True
    for kind, _ in ALLOWED_CASES:
        assert B.is_forbidden(kind) is False


def test_publish_email_account_login_denied():
    for kind in (K.PUBLISH_SOCIAL, K.SEND_EMAIL, K.CREATE_ACCOUNT, K.LOGIN_FORM_SUBMIT):
        assert _decide(kind).decision == D.DENY


def test_oea_ter_srp_denied():
    for kind in (K.START_OEA, K.START_TER, K.APPLY_SRP):
        assert _decide(kind).decision == D.DENY


def test_memory_and_source_mutation_denied():
    assert _decide(K.MUTATE_MEMORY).decision == D.DENY
    assert _decide(K.MUTATE_SOURCE).decision == D.DENY


def test_soak_live_mic_playback_loop_denied():
    for kind in (K.START_SOAK, K.ENABLE_LIVE_MIC, K.ENABLE_PLAYBACK, K.START_AUTONOMOUS_LOOP):
        assert _decide(kind).decision == D.DENY
