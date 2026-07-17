"""Internal power boundary pre-EXCITON slice tests."""

from __future__ import annotations

from hg_runtime.internal_power_boundary.evaluator import evaluate_internal_decision
from hg_runtime.internal_power_boundary.types import FIXTURE_CLOCK, autonomy_envelope_from_fixture, internal_decision_from_fixture


def test_no_self_authorization():
    decision = internal_decision_from_fixture(
        {"decision_id": "ipb-auth", "decision_class": "authority_chain_fake", "statement": "I authorize myself."}
    )
    envelope = autonomy_envelope_from_fixture({"envelope_id": "ipb-env"})
    result = evaluate_internal_decision(decision, envelope=envelope, observed_at=FIXTURE_CLOCK)
    assert result.get("status") == "refused" or "REFUSED" in str(result.get("reason_code", ""))
