"""Live read endurance receipt tests."""
from __future__ import annotations

from datetime import datetime, timezone

from hg_runtime.live_read_endurance.live_read_receipts import build_endurance_receipt
from hg_runtime.live_read_endurance.schema import LiveReadEnduranceVerdict
from hg_runtime.social_capability.live_bridge import LiveReadItem, LiveReadResult
from hg_runtime.social_capability.read_receipts import (
    LiveReadCredentialStatus,
    LiveReadReceipt,
    LiveReadVerdict,
)


def _bridge_result(*, item_count: int = 1, verdict: LiveReadVerdict = LiveReadVerdict.GREEN_LIVE_READ_OK) -> LiveReadResult:
    now = datetime.now(timezone.utc).isoformat()
    items = []
    for i in range(item_count):
        items.append(
            LiveReadItem(
                source_ref=f"ref-{i}",
                surface="moltbook",
                item_kind="post",
                observed_at=now,
                body_preview="preview",
                body_hash=f"hash-{i}",
            )
        )
    receipt = LiveReadReceipt(
        receipt_id="rcpt-1",
        request_id="req-1",
        surface="moltbook",
        runtime_mode="local_dev",
        fixture_mode=False,
        credential_status=LiveReadCredentialStatus.CREDENTIALS_PRESENT,
        api_called=True,
        api_call_kind="list",
        item_count=item_count,
        source_refs=tuple(f"ref-{i}" for i in range(item_count)),
        read_started_at=now,
        read_finished_at=now,
        latency_ms=10,
        verdict=verdict,
    )
    return LiveReadResult(
        request_id="req-1",
        surface="moltbook",
        items=items,
        receipt=receipt,
        verdict=verdict,
        credential_status=LiveReadCredentialStatus.CREDENTIALS_PRESENT,
    )


def test_receipt_requires_source_ref():
    result = _bridge_result(item_count=1)
    receipt = build_endurance_receipt(result=result, credential_scope_ref="scope-1", source_ref_primary="ref-0")
    assert receipt.source_ref
    assert receipt.hash


def test_receipt_hash_deterministic():
    result = _bridge_result(item_count=1)
    a = build_endurance_receipt(result=result, credential_scope_ref="scope-1", source_ref_primary="ref-0")
    b = build_endurance_receipt(result=result, credential_scope_ref="scope-1", source_ref_primary="ref-0")
    assert a.hash == b.hash


def test_empty_fresh_yellow():
    result = _bridge_result(item_count=0, verdict=LiveReadVerdict.YELLOW_NO_ITEMS_RETURNED)
    receipt = build_endurance_receipt(result=result, credential_scope_ref="scope-1", source_ref_primary="ref-0")
    assert receipt.verdict == LiveReadEnduranceVerdict.YELLOW_LIVE_READ_EMPTY_BUT_FRESH


def test_fixture_not_live():
    result = _bridge_result(item_count=0, verdict=LiveReadVerdict.RED_FIXTURE_FEED_USED_IN_RUNTIME)
    receipt = build_endurance_receipt(result=result, credential_scope_ref="scope-1", source_ref_primary="ref-0")
    assert receipt.verdict == LiveReadEnduranceVerdict.RED_FIXTURE_FEED_TREATED_AS_LIVE
