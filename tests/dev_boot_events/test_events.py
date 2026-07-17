"""Dev boot event tests."""

from __future__ import annotations

import pytest

from hg_runtime.agent0_dev_boot.events import DevBootEvent, validate_event_sequence
from hg_runtime.agent0_dev_boot.types import FIXTURE_CLOCK


def test_event_hash_stable() -> None:
    ev = DevBootEvent("Agent0WakeRequested", "run:1", 0, FIXTURE_CLOCK, "req:1")
    p1 = ev.to_payload()
    p2 = ev.to_payload()
    assert p1["event_hash"] == p2["event_hash"]


def test_missing_final_digest_fails() -> None:
    ev = DevBootEvent("Agent0WakeRequested", "run:1", 0, FIXTURE_CLOCK, "req:1").to_payload()
    ok, msg = validate_event_sequence([ev])
    assert ok is False
    assert "RuntimeFinalDigest" in msg


def test_permission_rejected() -> None:
    ev = {"sequence": 0, "event_type": "RuntimeFinalDigest", "permission_granted": True, "authority_created": False}
    ok, _ = validate_event_sequence([ev])
    assert ok is False
