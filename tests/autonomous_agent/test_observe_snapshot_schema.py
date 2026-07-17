"""ObserveSnapshot schema tests."""

from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.agent_zero_state.observe_snapshot import build_observe_snapshot  # noqa: E402
from hg_runtime.agent_zero_state.types import ObserveSnapshotVerdict  # noqa: E402


def test_observe_snapshot_no_receipts_cannot_be_green():
    verdict, snap = build_observe_snapshot(
        agent_id="agent-1",
        turn_index=0,
        runtime_mode="local_dev",
        provider_reality_refs=[],
        live_read_receipt_refs=[],
    )
    assert verdict != ObserveSnapshotVerdict.GREEN_OBSERVE_SNAPSHOT_READY


def test_observe_snapshot_provider_unavailable_is_yellow():
    verdict, _ = build_observe_snapshot(
        agent_id="agent-1",
        turn_index=0,
        runtime_mode="local_dev",
        provider_reality_refs=[],
        live_read_receipt_refs=["live-read-rcpt-abc"],
    )
    assert verdict == ObserveSnapshotVerdict.YELLOW_PROVIDER_UNAVAILABLE


def test_observe_snapshot_live_read_unavailable_is_yellow():
    verdict, _ = build_observe_snapshot(
        agent_id="agent-1",
        turn_index=0,
        runtime_mode="local_dev",
        provider_reality_refs=["provider-rcpt-xyz"],
        live_read_receipt_refs=[],
    )
    assert verdict == ObserveSnapshotVerdict.YELLOW_LIVE_READ_UNAVAILABLE


def test_observe_snapshot_fixture_runtime_rejected():
    verdict, _ = build_observe_snapshot(
        agent_id="agent-1",
        turn_index=0,
        runtime_mode="fixture",
        provider_reality_refs=["provider-rcpt-1"],
        live_read_receipt_refs=["live-read-1"],
    )
    assert verdict == ObserveSnapshotVerdict.RED_OBSERVE_FIXTURE_RUNTIME


def test_observe_snapshot_green_with_refs():
    verdict, snap = build_observe_snapshot(
        agent_id="agent-1",
        turn_index=1,
        runtime_mode="local_dev",
        provider_reality_refs=["provider-rcpt-1"],
        live_read_receipt_refs=["live-read-1"],
        data_tiers=["live", "internal"],
    )
    assert verdict == ObserveSnapshotVerdict.GREEN_OBSERVE_SNAPSHOT_READY
    assert snap.hash
