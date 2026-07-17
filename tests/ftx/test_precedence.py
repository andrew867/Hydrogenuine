"""CT-05 precedence tests."""

from __future__ import annotations

from hg_core.failures.precedence import resolve_aggregate_from_reason_codes, resolve_aggregate_state


def test_ftx_u4_panic_beats_failed() -> None:
    state = resolve_aggregate_state(["failed", "panic", "refused"])
    assert state == "panic"


def test_ftx_u5_refused_vs_policy_violation() -> None:
    refused = resolve_aggregate_from_reason_codes(["ter.refused.not_on_allowlist"])
    policy = resolve_aggregate_from_reason_codes(["iam.denied.policy_violation"])
    assert refused == "refused"
    assert policy == "policy_violation"
