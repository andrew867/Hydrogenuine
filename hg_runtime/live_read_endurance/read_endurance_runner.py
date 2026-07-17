"""Live read endurance runner — read-once and bounded smoke."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

from hg_runtime.agent_turn_engine.engine import run_single_agent_turn
from hg_runtime.agent_turn_engine.schema import build_agent_turn_request
from hg_runtime.live_read_endurance.credential_scope import check_credential_scope
from hg_runtime.live_read_endurance.errors import LiveReadWriteScopeDetected
from hg_runtime.live_read_endurance.freshness import assess_freshness
from hg_runtime.live_read_endurance.live_read_receipts import (
    build_endurance_receipt,
    latest_endurance_receipt,
    persist_endurance_receipt,
)
from hg_runtime.live_read_endurance.schema import (
    LiveReadEnduranceResult,
    LiveReadEnduranceVerdict,
    LiveReadFreshnessStatus,
    now_iso,
)
from hg_runtime.live_read_endurance.source_refs import build_source_refs_from_result
from hg_runtime.live_provider.provider_health import health_status_summary
from hg_runtime.social_capability.live_bridge import LiveReadSurface, live_read_enabled, read_surface_live
from hg_runtime.social_capability.read_receipts import LiveReadVerdict, verdict_counts_as_success

WORKSPACE = Path(__file__).resolve().parents[2]


def _pick_surface() -> LiveReadSurface:
    env = os.environ.get("HG_LIVE_READ_SURFACE", "moltbook").lower()
    if env == "fourclaw":
        return LiveReadSurface.FOURCLAW
    return LiveReadSurface.MOLTBOOK


def read_once(*, surface: LiveReadSurface | None = None, limit: int = 10) -> dict[str, Any]:
    from hg_runtime.social_capability.credentials import enforce_live_read_only_env, load_operator_social_env

    load_operator_social_env()
    enforce_live_read_only_env()
    surface = surface or _pick_surface()
    try:
        scope = check_credential_scope(surface)
    except LiveReadWriteScopeDetected:
        return {
            "verdict": LiveReadEnduranceVerdict.RED_LIVE_READ_WRITE_SCOPE_DETECTED.value,
            "credential_values_printed": False,
        }

    if scope.verdict == LiveReadEnduranceVerdict.YELLOW_LIVE_READ_CREDENTIALS_MISSING:
        return {
            "verdict": scope.verdict.value,
            "credential_scope_ref": scope.credential_scope_id,
            "credential_values_printed": False,
            "live_read_enabled": live_read_enabled(),
        }

    request_id = f"read-{uuid.uuid4().hex[:12]}"
    result = read_surface_live(surface, limit=limit, request_id=request_id)
    freshness_status, _ = assess_freshness(
        read_verdict=result.verdict,
        item_count=len(result.items),
        read_completed_at=result.receipt.read_finished_at or result.receipt.read_started_at,
    )
    source_refs = build_source_refs_from_result(result, freshness_status=freshness_status)
    primary_ref = source_refs[0].source_ref_id if source_refs else scope.credential_scope_id
    endurance_receipt = build_endurance_receipt(
        result=result,
        credential_scope_ref=scope.credential_scope_id,
        source_ref_primary=primary_ref,
    )
    receipt_path = persist_endurance_receipt(endurance_receipt)

    return {
        "verdict": endurance_receipt.verdict.value,
        "bridge_verdict": result.verdict.value,
        "item_count": len(result.items),
        "freshness_status": freshness_status.value,
        "live_read_receipt_id": endurance_receipt.live_read_receipt_id,
        "receipt_path": str(receipt_path.relative_to(WORKSPACE)),
        "receipt_hash": endurance_receipt.hash,
        "source_ref_count": len(source_refs),
        "source_refs_hash": source_refs[0].hash if source_refs else None,
        "credential_scope_ref": scope.credential_scope_id,
        "credential_values_printed": False,
        "data_tier": result.data_tier,
        "success": verdict_counts_as_success(result.verdict),
    }


def probe_live_read_status(*, surface: LiveReadSurface | None = None) -> dict[str, Any]:
    outcome = read_once(surface=surface, limit=5)
    status = "unavailable"
    if outcome.get("success"):
        status = "available"
    elif outcome.get("verdict", "").startswith("YELLOW_"):
        status = "degraded"
    elif outcome.get("verdict", "").startswith("RED_"):
        status = "blocked"
    return {
        "status": status,
        "verdict": outcome.get("verdict"),
        "receipt_ref": outcome.get("live_read_receipt_id"),
        "freshness_status": outcome.get("freshness_status"),
        "item_count": outcome.get("item_count", 0),
    }


def collect_for_observe_snapshot(*, surface: LiveReadSurface | None = None) -> tuple[list[str], str | None, str]:
    if not live_read_enabled():
        return [], "credentials_missing", LiveReadFreshnessStatus.CREDENTIALS_MISSING.value
    outcome = read_once(surface=surface, limit=10)
    receipt_id = outcome.get("live_read_receipt_id")
    refs = [receipt_id] if receipt_id else []
    cred = "credentials_missing" if "CREDENTIALS_MISSING" in outcome.get("verdict", "") else "present"
    freshness = outcome.get("freshness_status") or LiveReadFreshnessStatus.UNAVAILABLE.value
    return refs, cred, freshness


def run_endurance_smoke(*, run_id: str, max_iterations: int = 3) -> LiveReadEnduranceResult:
    receipts = []
    all_refs = []
    final_verdict = LiveReadEnduranceVerdict.YELLOW_LIVE_READ_CREDENTIALS_MISSING
    live_status = "unavailable"
    for _ in range(max(1, max_iterations)):
        outcome = read_once(limit=5)
        live_status = outcome.get("verdict", live_status)
        if outcome.get("live_read_receipt_id"):
            latest = latest_endurance_receipt()
            if latest:
                from hg_runtime.live_read_endurance.schema import LiveReadEnduranceReceipt

                receipts.append(
                    LiveReadEnduranceReceipt(
                        live_read_receipt_id=latest["live_read_receipt_id"],
                        source_ref=latest["source_ref"],
                        source_kind=latest["source_kind"],
                        source_name=latest["source_name"],
                        read_started_at=latest["read_started_at"],
                        read_completed_at=latest["read_completed_at"],
                        credential_scope_ref=latest["credential_scope_ref"],
                        item_count=int(latest["item_count"]),
                        items_hash=latest["items_hash"],
                        freshness_ref=latest["freshness_ref"],
                        data_tier=latest["data_tier"],
                        verdict=LiveReadEnduranceVerdict(latest["verdict"]),
                        fixture_label=latest.get("fixture_label"),
                        hash=latest.get("hash"),
                    )
                )
        if outcome.get("success"):
            final_verdict = LiveReadEnduranceVerdict.GREEN_LIVE_READ_ENDURANCE_COMPLETE
        elif "CREDENTIALS_MISSING" in outcome.get("verdict", ""):
            final_verdict = LiveReadEnduranceVerdict.YELLOW_LIVE_READ_CREDENTIALS_MISSING
        elif outcome.get("verdict"):
            try:
                final_verdict = LiveReadEnduranceVerdict(outcome["verdict"])
            except ValueError:
                final_verdict = LiveReadEnduranceVerdict.YELLOW_LIVE_READ_SOURCE_CONFIGURED_BUT_UNAVAILABLE

    provider = health_status_summary()
    return LiveReadEnduranceResult(
        run_id=run_id,
        iterations=max_iterations,
        receipts=receipts,
        source_refs=all_refs,
        verdict=final_verdict,
        provider_status="available" if provider.get("available") else "unavailable",
        live_read_status=live_status,
    )


def run_dry_turn(*, run_id: str) -> dict[str, Any]:
    request = build_agent_turn_request(
        run_id=run_id,
        agent_id="zero",
        runtime_mode="local_dev",
        allow_provider=True,
        allow_live_read=True,
        operator_presence="operator_present",
    )
    outcome = run_single_agent_turn(request)
    return {
        "turn_verdict": outcome.verdict.value,
        "turn_receipt_ref": outcome.turn_receipt_ref,
        "observe_snapshot_ref": outcome.observe_snapshot_ref,
        "credential_values_printed": False,
    }
