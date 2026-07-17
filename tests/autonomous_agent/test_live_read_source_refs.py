"""Live read source ref tests."""
from __future__ import annotations

from datetime import datetime, timezone

from hg_runtime.live_read_endurance.schema import LiveReadFreshnessStatus, LiveReadSourceRef, new_id, now_iso
from hg_runtime.live_read_endurance.source_refs import build_source_refs_from_result
from hg_runtime.social_capability.live_bridge import LiveReadResult
from hg_runtime.social_capability.read_receipts import (
    LiveReadCredentialStatus,
    LiveReadReceipt,
    LiveReadVerdict,
)


def _empty_result() -> LiveReadResult:
    now = datetime.now(timezone.utc).isoformat()
    receipt = LiveReadReceipt(
        receipt_id="rcpt-2",
        request_id="req-2",
        surface="moltbook",
        runtime_mode="local_dev",
        fixture_mode=False,
        credential_status=LiveReadCredentialStatus.CREDENTIALS_PRESENT,
        api_called=True,
        api_call_kind="list",
        item_count=0,
        source_refs=("legacy-ref",),
        read_started_at=now,
        read_finished_at=now,
        latency_ms=5,
        verdict=LiveReadVerdict.YELLOW_NO_ITEMS_RETURNED,
    )
    return LiveReadResult(
        request_id="req-2",
        surface="moltbook",
        items=[],
        receipt=receipt,
        verdict=LiveReadVerdict.YELLOW_NO_ITEMS_RETURNED,
        credential_status=LiveReadCredentialStatus.CREDENTIALS_PRESENT,
    )


def test_source_ref_hash_deterministic():
    ref = LiveReadSourceRef(
        source_ref_id="fixed-ref",
        source_kind="moltbook",
        source_name="moltbook",
        observed_at="2026-06-16T00:00:00+00:00",
        freshness_status=LiveReadFreshnessStatus.EMPTY_BUT_FRESH,
        data_tier="LIVE",
    ).with_hash()
    again = LiveReadSourceRef(
        source_ref_id="fixed-ref",
        source_kind="moltbook",
        source_name="moltbook",
        observed_at="2026-06-16T00:00:00+00:00",
        freshness_status=LiveReadFreshnessStatus.EMPTY_BUT_FRESH,
        data_tier="LIVE",
    ).with_hash()
    assert ref.hash == again.hash


def test_build_refs_from_empty_result():
    refs = build_source_refs_from_result(_empty_result(), freshness_status=LiveReadFreshnessStatus.EMPTY_BUT_FRESH)
    assert len(refs) >= 1
    assert refs[0].freshness_status == LiveReadFreshnessStatus.EMPTY_BUT_FRESH
