"""Witness integrity tests."""

from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.bounded_soak.witness_integrity import (  # noqa: E402
    WitnessIntegrityVerdict,
    WitnessMode,
    build_witness_receipt,
    enter_witness_mode,
    validate_witness_receipt,
)


def test_witness_receipt_requires_nonempty_reason():
    verdict, receipt = enter_witness_mode(mode=WitnessMode.REST, reason="")
    assert verdict == WitnessIntegrityVerdict.RED_WITNESS_RECEIPT_EMPTY
    assert validate_witness_receipt(receipt) == WitnessIntegrityVerdict.RED_WITNESS_RECEIPT_EMPTY


def test_witness_receipt_cannot_allow_external_action():
    receipt = build_witness_receipt(
        mode=WitnessMode.OBSERVE_ONLY,
        reason="observing only",
        operator_present=False,
    )
    assert receipt.external_action_allowed is False
    bad = build_witness_receipt(
        mode=WitnessMode.OBSERVE_ONLY,
        reason="test",
        operator_present=False,
    )
    object.__setattr__(bad, "external_action_allowed", True)  # type: ignore[misc]
    assert validate_witness_receipt(bad) == WitnessIntegrityVerdict.RED_WITNESS_EXTERNAL_ACTION


def test_witness_receipt_cannot_expand_authority():
    receipt = build_witness_receipt(
        mode=WitnessMode.REST,
        reason="rest chosen",
        operator_present=False,
    )
    assert receipt.authority_expanded is False


def test_witness_receipt_cannot_override_stop_panic():
    receipt = build_witness_receipt(
        mode=WitnessMode.FAIL_STILL,
        reason="system unavailable",
        operator_present=False,
    )
    assert receipt.stop_panic_override is False
    assert validate_witness_receipt(receipt) == WitnessIntegrityVerdict.GREEN_WITNESS_RECEIPT_VALID


def test_witness_hash_deterministic():
    r1 = build_witness_receipt(
        mode=WitnessMode.REST,
        reason="rest",
        operator_present=False,
        receipt_id="witness-fixed-id",
        created_at="2026-06-17T00:00:00+00:00",
    )
    r2 = build_witness_receipt(
        mode=WitnessMode.REST,
        reason="rest",
        operator_present=False,
        receipt_id="witness-fixed-id",
        created_at="2026-06-17T00:00:00+00:00",
    )
    assert r1.hash == r2.hash
    assert len(r1.hash) > 0
