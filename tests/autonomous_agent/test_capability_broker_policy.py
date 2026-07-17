"""Capability broker policy tests."""

from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.capability_broker.policy import load_capability_broker_policy  # noqa: E402


def test_policy_denies_external_side_effects():
    policy = load_capability_broker_policy()
    assert policy.external_side_effects_allowed is False
    assert policy.live_writes_allowed is False
    assert policy.operator_absence_expands_authority is False
    assert policy.fixture_runtime_truth_allowed is False
    assert policy.dry_run_action_admission_allowed is False


def test_policy_requires_decision_hash():
    policy = load_capability_broker_policy()
    assert policy.decision_hash_required is True
    assert policy.decision_receipt_required is True
