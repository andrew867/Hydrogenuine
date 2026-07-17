"""EXCITON live read monitor snapshot."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from hg_runtime.live_read_endurance.live_read_receipts import latest_endurance_receipt
from hg_runtime.live_read_endurance.schema import LiveReadEnduranceVerdict, LiveReadFreshnessStatus
from hg_runtime.social_capability.live_bridge import live_read_enabled, live_writes_disabled


def _freshness_from_receipt(receipt: dict[str, Any] | None, *, max_stale_seconds: int = 900) -> str:
    if not receipt:
        return "missing"
    completed = receipt.get("read_completed_at")
    if not completed:
        return "missing"
    try:
        ts = datetime.fromisoformat(completed.replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - ts).total_seconds()
        if age > max_stale_seconds:
            return LiveReadFreshnessStatus.STALE.value
    except ValueError:
        return LiveReadFreshnessStatus.INVALID.value
    if int(receipt.get("item_count", 0)) == 0:
        return LiveReadFreshnessStatus.EMPTY_BUT_FRESH.value
    return LiveReadFreshnessStatus.FRESH.value


def build_monitor_fields(*, observe_snapshot_ref: str | None = None) -> dict[str, Any]:
    from hg_runtime.live_read_endurance.credential_scope import credential_summary
    from hg_runtime.live_provider.exciton_snapshot import build_provider_monitor_fields

    cred = credential_summary()
    receipt = latest_endurance_receipt()
    provider = build_provider_monitor_fields()
    freshness = _freshness_from_receipt(receipt)
    write_scope = cred.get("write_scope_detected", False)
    if not write_scope:
        from hg_runtime.live_read_endurance.credential_scope import _write_scope_detected

        write_scope = _write_scope_detected()

    if write_scope:
        verdict = LiveReadEnduranceVerdict.RED_LIVE_READ_WRITE_SCOPE_DETECTED.value
    elif not live_read_enabled():
        verdict = LiveReadEnduranceVerdict.YELLOW_LIVE_READ_CREDENTIALS_MISSING.value
    elif not receipt:
        verdict = LiveReadEnduranceVerdict.YELLOW_LIVE_READ_CREDENTIALS_MISSING.value
    elif freshness == LiveReadFreshnessStatus.STALE.value:
        verdict = LiveReadEnduranceVerdict.YELLOW_LIVE_READ_STALE.value
    elif freshness == LiveReadFreshnessStatus.EMPTY_BUT_FRESH.value:
        verdict = LiveReadEnduranceVerdict.YELLOW_LIVE_READ_EMPTY_BUT_FRESH.value
    elif receipt.get("data_tier") not in (None, "LIVE"):
        verdict = LiveReadEnduranceVerdict.RED_FIXTURE_FEED_TREATED_AS_LIVE.value
    elif receipt.get("verdict", "").startswith("GREEN_"):
        verdict = LiveReadEnduranceVerdict.GREEN_LIVE_READ_ENDURANCE_COMPLETE.value
    else:
        verdict = receipt.get("verdict", LiveReadEnduranceVerdict.YELLOW_LIVE_READ_CREDENTIALS_MISSING.value)

    return {
        "panel_title": "Agent Zero Live Read Monitor",
        "source_kind": receipt.get("source_kind") if receipt else None,
        "source_name": receipt.get("source_name") if receipt else None,
        "credential_scope_status": cred.get("scopes", []),
        "read_only_status": live_writes_disabled(),
        "write_scope_detected": write_scope,
        "last_read_receipt": receipt.get("live_read_receipt_id") if receipt else None,
        "item_count": receipt.get("item_count") if receipt else 0,
        "freshness": freshness,
        "source_refs_count": int(receipt.get("item_count", 0)) if receipt else 0,
        "data_tier": receipt.get("data_tier") if receipt else "none",
        "fixture_label": (receipt or {}).get("fixture_label"),
        "provider_status": provider.get("provider_status"),
        "last_observe_snapshot_ref": observe_snapshot_ref,
        "verdict": verdict,
        "truth_state": verdict,
        "publish_available": False,
        "send_available": False,
        "reply_available": False,
        "comment_available": False,
        "browser_available": False,
        "direct_external_actions_allowed": False,
    }
