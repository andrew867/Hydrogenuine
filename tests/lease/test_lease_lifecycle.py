"""Lease lifecycle state machine: exhaustive transition coverage."""

import pytest

from hg_lease.lease import (
    CapabilityLease,
    LeaseTransitionError,
    STATES,
    TERMINAL_STATES,
    TRANSITIONS,
    apply_transition,
    consume_use,
)

NOW = "2026-07-17T12:00:00.000000Z"
EVENTS = sorted({event for (_, event) in TRANSITIONS})


def make_lease(state="DRAFT", remaining_uses=None):
    return CapabilityLease(
        lease_id="lease_test",
        policy_id="pol_test",
        policy_hash="sha256:x",
        issuer="op:local",
        subject="agent:zero",
        action_scope=("open_window",),
        object_scope=("window:kitchen_west",),
        purpose_scope=("ventilation",),
        issued_at_wall=NOW,
        issued_at_monotonic_anchor=100.0,
        not_before=NOW,
        expires_at="2026-07-24T12:00:00.000000Z",
        risk_class="LOW",
        state=state,
        remaining_uses=remaining_uses,
    )


def test_every_declared_transition_applies():
    for (from_state, event), to_state in TRANSITIONS.items():
        lease = make_lease(state=from_state)
        updated, lifecycle = apply_transition(
            lease, event, event_id=f"e:{from_state}:{event}",
            reason_code="test", now_wall=NOW,
        )
        assert updated.state == to_state
        assert lifecycle is not None
        assert lifecycle.from_state == from_state
        assert lifecycle.to_state == to_state


def test_every_undeclared_transition_fails_closed():
    for state in STATES:
        for event in EVENTS:
            if (state, event) in TRANSITIONS:
                continue
            lease = make_lease(state=state)
            with pytest.raises(LeaseTransitionError):
                apply_transition(
                    lease, event, event_id="e:bad",
                    reason_code="test", now_wall=NOW,
                )


def test_terminal_states_accept_nothing():
    for state in TERMINAL_STATES:
        assert not any(s == state for (s, _) in TRANSITIONS), (
            f"terminal state {state} has outgoing transitions"
        )


def test_transition_is_idempotent_per_event_id():
    lease = make_lease(state="ACTIVE")
    lease2, ev = apply_transition(
        lease, "suspend", event_id="e:1", reason_code="test", now_wall=NOW
    )
    assert lease2.state == "SUSPENDED" and ev is not None
    lease3, ev2 = apply_transition(
        lease2, "suspend", event_id="e:1", reason_code="test", now_wall=NOW
    )
    assert lease3 is lease2 and ev2 is None  # no-op replay


def test_replayed_event_id_does_not_double_apply_after_resume():
    lease = make_lease(state="ACTIVE")
    lease, _ = apply_transition(lease, "suspend", event_id="e:s", reason_code="t", now_wall=NOW)
    lease, _ = apply_transition(lease, "resume", event_id="e:r", reason_code="t", now_wall=NOW)
    replayed, ev = apply_transition(lease, "suspend", event_id="e:s", reason_code="t", now_wall=NOW)
    assert ev is None and replayed.state == "ACTIVE"


def test_consume_use_counts_down_and_exhausts():
    lease = make_lease(state="ACTIVE", remaining_uses=2)
    lease, exhausted = consume_use(lease)
    assert lease.remaining_uses == 1 and not exhausted
    lease, exhausted = consume_use(lease)
    assert lease.remaining_uses == 0 and exhausted
    lease, exhausted = consume_use(lease)
    assert lease.remaining_uses == 0 and exhausted


def test_unlimited_lease_never_exhausts():
    lease = make_lease(state="ACTIVE", remaining_uses=None)
    lease, exhausted = consume_use(lease)
    assert not exhausted and lease.remaining_uses is None


def test_lease_hash_changes_with_state():
    a = make_lease(state="ACTIVE")
    b = make_lease(state="SUSPENDED")
    assert a.lease_hash != b.lease_hash
