"""Endurance-layer live read receipts wrapping Phase 4 bridge."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from hg_runtime.live_read_endurance.freshness import assess_freshness
from hg_runtime.live_read_endurance.schema import (
    LiveReadEnduranceReceipt,
    LiveReadEnduranceVerdict,
    LiveReadFreshnessStatus,
    new_id,
)
from hg_runtime.social_capability.live_bridge import LiveReadResult
from hg_runtime.social_capability.read_receipts import LiveReadVerdict

WORKSPACE = Path(__file__).resolve().parents[2]
RECEIPT_STORE = WORKSPACE / ".hg-local/live_read_endurance/receipts"


def _items_hash(items: list[Any]) -> str:
    payload = json.dumps([getattr(i, "to_payload", lambda: i)() for i in items], sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def bridge_verdict_to_endurance(bridge_verdict: LiveReadVerdict, freshness: LiveReadFreshnessStatus) -> LiveReadEnduranceVerdict:
    if bridge_verdict == LiveReadVerdict.RED_FIXTURE_FEED_USED_IN_RUNTIME:
        return LiveReadEnduranceVerdict.RED_FIXTURE_FEED_TREATED_AS_LIVE
    if freshness == LiveReadFreshnessStatus.STALE:
        return LiveReadEnduranceVerdict.YELLOW_LIVE_READ_STALE
    if freshness == LiveReadFreshnessStatus.EMPTY_BUT_FRESH:
        return LiveReadEnduranceVerdict.YELLOW_LIVE_READ_EMPTY_BUT_FRESH
    if freshness == LiveReadFreshnessStatus.CREDENTIALS_MISSING:
        return LiveReadEnduranceVerdict.YELLOW_LIVE_READ_CREDENTIALS_MISSING
    if bridge_verdict == LiveReadVerdict.GREEN_LIVE_READ_OK:
        return LiveReadEnduranceVerdict.GREEN_LIVE_READ_ENDURANCE_COMPLETE
    if bridge_verdict == LiveReadVerdict.YELLOW_NO_ITEMS_RETURNED:
        return LiveReadEnduranceVerdict.YELLOW_LIVE_READ_EMPTY_BUT_FRESH
    return LiveReadEnduranceVerdict.YELLOW_LIVE_READ_SOURCE_CONFIGURED_BUT_UNAVAILABLE


def build_endurance_receipt(
    *,
    result: LiveReadResult,
    credential_scope_ref: str,
    source_ref_primary: str,
) -> LiveReadEnduranceReceipt:
    receipt = result.receipt
    finished = receipt.read_finished_at or receipt.read_started_at
    freshness_status, freshness_ref = assess_freshness(
        read_verdict=result.verdict,
        item_count=len(result.items),
        read_completed_at=finished,
    )
    freshness_ref = f"fresh-{finished}-{len(result.items)}-{result.verdict.value}"
    verdict = bridge_verdict_to_endurance(result.verdict, freshness_status)
    endurance = LiveReadEnduranceReceipt(
        live_read_receipt_id=receipt.receipt_id or new_id("live-read"),
        source_ref=source_ref_primary,
        source_kind=result.surface,
        source_name=result.surface,
        read_started_at=receipt.read_started_at,
        read_completed_at=finished,
        credential_scope_ref=credential_scope_ref,
        item_count=len(result.items),
        items_hash=_items_hash(result.items),
        freshness_ref=freshness_ref,
        data_tier=result.data_tier,
        fixture_label=None if result.data_tier == "LIVE" else result.data_tier,
        verdict=verdict,
    ).with_hash()
    return endurance


def persist_endurance_receipt(receipt: LiveReadEnduranceReceipt, *, base: Path | None = None) -> Path:
    root = base or RECEIPT_STORE
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{receipt.live_read_receipt_id}.json"
    path.write_text(json.dumps(receipt.to_payload(), indent=2) + "\n", encoding="utf-8")
    return path


def load_endurance_receipt(receipt_id: str, *, base: Path | None = None) -> dict[str, Any] | None:
    root = base or RECEIPT_STORE
    path = root / f"{receipt_id}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def latest_endurance_receipt(*, base: Path | None = None) -> dict[str, Any] | None:
    root = base or RECEIPT_STORE
    if not root.is_dir():
        return None
    files = sorted(root.glob("*.json"), reverse=True)
    if not files:
        return None
    return json.loads(files[0].read_text(encoding="utf-8"))
