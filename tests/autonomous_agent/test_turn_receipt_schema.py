"""TurnReceipt schema tests."""

from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.agent_zero_state.turn_receipt import (  # noqa: E402
    TurnReceipt,
    TurnReceiptVerdict,
    build_turn_receipt,
    validate_turn_receipt,
)


def _base_receipt(**kwargs) -> TurnReceipt:
    defaults = dict(
        agent_id="agent-1",
        turn_index=1,
        runtime_mode="local_dev",
        observe_snapshot_ref="snap-1",
        capability_menu_ref="menu-1",
        chosen_action="synthesize_notes",
        provider_receipt_refs=["provider-rcpt-1"],
        live_read_receipt_refs=["live-read-1"],
    )
    defaults.update(kwargs)
    _, receipt = build_turn_receipt(**defaults)
    return receipt


def test_turn_receipt_requires_observe_snapshot_ref():
    verdict, _ = build_turn_receipt(
        agent_id="agent-1",
        turn_index=1,
        runtime_mode="local_dev",
        observe_snapshot_ref="",
        capability_menu_ref="menu-1",
        chosen_action="rest_turn",
    )
    assert verdict == TurnReceiptVerdict.RED_TURN_WITHOUT_OBSERVE


def test_turn_receipt_rejects_external_side_effect():
    receipt = _base_receipt()
    bad = TurnReceipt(
        **{**receipt.__dict__, "external_side_effect": True, "published": True}
    )
    verdict, _ = validate_turn_receipt(bad.with_hash())
    assert verdict == TurnReceiptVerdict.RED_TURN_EXTERNAL_SIDE_EFFECT


def test_turn_receipt_rejects_publish_send_flags():
    receipt = _base_receipt()
    bad = TurnReceipt(**{**receipt.__dict__, "sent": True})
    verdict, _ = validate_turn_receipt(bad.with_hash())
    assert verdict == TurnReceiptVerdict.RED_TURN_EXTERNAL_SIDE_EFFECT


def test_turn_receipt_hash_deterministic():
    r1 = _base_receipt(receipt_id="fixed-id", turn_started_at="2026-06-17T00:00:00+00:00", turn_finished_at="2026-06-17T00:00:01+00:00")
    r2 = _base_receipt(receipt_id="fixed-id", turn_started_at="2026-06-17T00:00:00+00:00", turn_finished_at="2026-06-17T00:00:01+00:00")
    assert r1.hash == r2.hash


def test_turn_receipt_previous_hash_chain():
    r1 = _base_receipt(turn_index=1, previous_turn_hash=None)
    r2 = _base_receipt(turn_index=2, previous_turn_hash=r1.hash, receipt_id="turn-2")
    assert r2.previous_turn_hash == r1.hash
