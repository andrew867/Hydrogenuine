"""Failure posture tests."""

from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.bounded_soak.failure_posture import (  # noqa: E402
    FailureKind,
    FailurePosture,
    evaluate_failure_posture,
    output_validator_failure_blocks_acceptance,
    provider_failure_denies_cognition,
)


def test_provider_unavailable_becomes_fail_still_not_fake_cognition():
    receipt = evaluate_failure_posture(failure_kind=FailureKind.PROVIDER_UNAVAILABLE)
    assert receipt.posture == FailurePosture.FAIL_STILL
    assert provider_failure_denies_cognition(receipt)
    assert receipt.fake_success_denied is True


def test_output_validator_unavailable_rejects_draft_acceptance():
    receipt = evaluate_failure_posture(failure_kind=FailureKind.OUTPUT_VALIDATOR_UNAVAILABLE)
    assert output_validator_failure_blocks_acceptance(receipt)


def test_stop_panic_uncertainty_escalates():
    receipt = evaluate_failure_posture(failure_kind=FailureKind.STOP_PANIC_UNCERTAIN)
    assert receipt.posture == FailurePosture.PANIC_REQUIRED


def test_unknown_failure_fails_still():
    receipt = evaluate_failure_posture(failure_kind=FailureKind.UNKNOWN)
    assert receipt.posture == FailurePosture.FAIL_STILL
    assert receipt.fake_success_denied is True
