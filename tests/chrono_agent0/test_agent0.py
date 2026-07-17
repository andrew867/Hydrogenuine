"""CHRONO Agent #0 time-context tests."""

from __future__ import annotations

from hg_runtime.chrono.agent0 import (
    AGENT0_TIME_INSTRUCTION,
    build_agent0_time_context,
    time_on_wake,
)
from hg_runtime.chrono.policy import validate_frozen_constants
from hg_runtime.chrono.schema import TimeConfidence, TimeSourceKind
from hg_runtime.chrono.sync import ChronoConfig, sync_time


def test_wake_returns_context_and_outcome():
    context, outcome = time_on_wake(ChronoConfig(offline_fixture=True))
    assert context.source == TimeSourceKind.FIXTURE
    assert context.receipt_ref == outcome.receipt.receipt_id


def test_context_frozen_constants_and_hash():
    context = build_agent0_time_context(sync_time(ChronoConfig(offline_fixture=True)))
    payload = context.to_payload()
    assert validate_frozen_constants(payload) == []
    assert payload["content_hash"].startswith("sha256:")


def test_low_confidence_marks_uncertain():
    context = build_agent0_time_context(sync_time(ChronoConfig(allow_network=False)))
    assert context.time_confidence == TimeConfidence.LOW
    assert context.time_uncertain is True


def test_instruction_block_is_evidence_not_authority():
    text = AGENT0_TIME_INSTRUCTION.lower()
    assert "evidence, not authority" in text
    assert "never state a date you did not receive" in text
