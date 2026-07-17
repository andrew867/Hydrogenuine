"""B12-B16 — identity disclosure, cost hard stop, degraded mode, interrupt, continuity."""

from __future__ import annotations

from hg_runtime.trust_boundary.guards import (
    ContinuityCheckpoint,
    CostHardStop,
    DegradedMode,
    IdentityDisclosure,
    OperatorInterrupt,
)
from hg_runtime.trust_boundary.schema import DegradedReason


def test_identity_disclosure_stamped_on_draft():
    stamped = IdentityDisclosure.stamp("Hello there")
    assert stamped["discloses_ai"] is True
    assert stamped["claims_consciousness"] is False
    assert IdentityDisclosure.is_disclosed(stamped["draft_with_disclosure"]) is True


def test_cost_hard_stop_halts_before_exceeding():
    stop = CostHardStop(budget_units=10.0)
    ok = stop.charge(6.0)
    assert ok["allowed"] is True
    blocked = stop.charge(6.0)
    assert blocked["allowed"] is False
    # Spend was not applied past the budget.
    assert stop.spent_units == 6.0


def test_degraded_mode_is_visible_not_silent():
    mode = DegradedMode()
    payload = mode.enter(DegradedReason.CLASSIFIER_OFFLINE)
    assert payload["active"] is True
    assert payload["visible"] is True
    assert payload["reason"] == "CLASSIFIER_OFFLINE"


def test_operator_interrupt_is_honored():
    intr = OperatorInterrupt()
    assert intr.should_stop() is False
    intr.request_stop()
    assert intr.should_stop() is True
    assert intr.checkpoint(where="model_wait")["stop_requested"] is True


def test_continuity_checkpoint_restores_labels():
    cp = ContinuityCheckpoint(labels={"d1": "UNTRUSTED_WEB"})
    snap = cp.snapshot()
    restored = ContinuityCheckpoint.restore(snap)
    assert restored.labels == {"d1": "UNTRUSTED_WEB"}


def test_guard_payloads_carry_frozen_constants():
    for payload in (
        IdentityDisclosure.stamp("x"),
        CostHardStop(budget_units=1.0).charge(0.5),
        DegradedMode().enter(DegradedReason.NETWORK_LOSS),
        OperatorInterrupt().checkpoint(where="x"),
        ContinuityCheckpoint().snapshot(),
    ):
        assert payload["advisory_only"] is True
        assert payload["permission_granted"] is False
        assert payload["authority_created"] is False
