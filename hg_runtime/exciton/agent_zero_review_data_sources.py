"""EXCITON Agent Zero operator review panel collectors — read-only."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from hg_runtime.agent_turn_engine.turn_storage import receipts_dir, run_dir as turn_run_dir
from hg_runtime.exciton.data_sources import CollectorContext, _panel
from hg_runtime.exciton.schema import ExcitonPanelState
from hg_runtime.operator_review.review_queue import build_review_queue_snapshot, snapshot_item_summaries
from hg_runtime.operator_review.review_store import ReviewStore, review_root
from hg_runtime.operator_review.schema import FreshnessStatus, ReviewQueueVerdict
from hg_runtime.operator_review.truth_state import truth_state_to_panel_fields
from hg_runtime.output_artifacts.artifact_store import ArtifactStore, artifacts_root


def _discover_run_id() -> str | None:
    env_run = os.environ.get("HG_AGENT_ZERO_RUN_ID")
    if env_run:
        return env_run
    root = artifacts_root()
    if not root.is_dir():
        return None
    runs = sorted([p.name for p in root.iterdir() if p.is_dir()], reverse=True)
    return runs[0] if runs else None


def _panel_state_from_verdict(verdict: str, freshness: FreshnessStatus) -> ExcitonPanelState:
    if verdict.startswith("RED_"):
        return ExcitonPanelState.RED
    if freshness == FreshnessStatus.STALE or verdict.startswith("YELLOW_"):
        return ExcitonPanelState.YELLOW
    if verdict.startswith("GREEN_"):
        return ExcitonPanelState.GREEN
    return ExcitonPanelState.UNKNOWN


def _build_review_queue_panel(ctx: CollectorContext) -> Any:
    run_id = _discover_run_id()
    if not run_id:
        return _panel(
            "AgentZeroReviewQueuePanel",
            ExcitonPanelState.RED,
            {
                "item_count": 0,
                "freshness_status": FreshnessStatus.MISSING.value,
                "source_refs": [],
                "source_ref_count": 0,
                "verdict": ReviewQueueVerdict.RED_REVIEW_QUEUE_EMPTY_GREEN_WITHOUT_SOURCE.value,
                "truth_state": ReviewQueueVerdict.RED_REVIEW_QUEUE_EMPTY_GREEN_WITHOUT_SOURCE.value,
                "generated_at": None,
                "expires_at": None,
                "items_summary": [],
                "direct_external_actions_allowed": False,
            },
            degraded_reason="no artifact source store",
        )

    snapshot = build_review_queue_snapshot(
        run_id,
        offline_fixture=ctx.offline_fixture,
        fixture_label="exciton_offline_fixture" if ctx.offline_fixture else None,
    )
    artifact_store = ArtifactStore(run_id)
    summaries = snapshot_item_summaries(snapshot, artifact_store)
    review_store = ReviewStore(run_id)
    truth_fields = []
    for item in snapshot.items:
        try:
            truth_payload = review_store.read_truth_state(item.truth_state_ref)
            truth_fields.append(truth_payload)
        except Exception:
            truth_fields.append({"truth_state_ref": item.truth_state_ref, "verdict": "RED_REVIEW_ITEM_SOURCE_MISSING"})

    fields = {
        "run_id": run_id,
        "item_count": snapshot.item_count,
        "freshness_status": snapshot.freshness_status.value,
        "source_refs": [snapshot.source_store_ref],
        "source_ref_count": 1,
        "source_store_ref": snapshot.source_store_ref,
        "generated_at": snapshot.generated_at,
        "expires_at": snapshot.expires_at,
        "verdict": snapshot.verdict.value,
        "truth_state": truth_fields[0].get("verdict", snapshot.verdict.value) if truth_fields else snapshot.verdict.value,
        "items_summary": summaries,
        "queue_verdict": snapshot.verdict.value,
        "direct_external_actions_allowed": False,
        "approve_available": False,
        "publish_available": False,
        "send_available": False,
        "data_tier": "FIXTURE" if ctx.offline_fixture else "LIVE",
    }
    state = _panel_state_from_verdict(snapshot.verdict.value, snapshot.freshness_status)
    return _panel("AgentZeroReviewQueuePanel", state, fields)


def _build_turn_trace_panel(ctx: CollectorContext) -> Any:
    run_id = _discover_run_id()
    if not run_id:
        return _panel(
            "AgentZeroTurnTracePanel",
            ExcitonPanelState.RED,
            {
                "freshness_status": FreshnessStatus.MISSING.value,
                "source_refs": [],
                "verdict": "RED_TURN_TRACE_SOURCE_MISSING",
                "truth_state": "RED_TURN_TRACE_SOURCE_MISSING",
            },
            degraded_reason="no turn storage",
        )

    tdir = turn_run_dir(run_id)
    receipt_files = sorted(receipts_dir(run_id).glob("*.json")) if receipts_dir(run_id).is_dir() else []
    latest_receipt: dict[str, Any] = {}
    if receipt_files:
        latest_receipt = json.loads(receipt_files[-1].read_text(encoding="utf-8"))

    fields = {
        "run_id": run_id,
        "turn_receipt_ref": latest_receipt.get("receipt_id"),
        "observe_snapshot_ref": latest_receipt.get("observe_snapshot_ref"),
        "capability_menu_ref": latest_receipt.get("capability_menu_ref"),
        "reasoning_result_ref": latest_receipt.get("reasoning_result_ref") or latest_receipt.get("reasoning_receipt_ref"),
        "reasoning_failure_ref": latest_receipt.get("reasoning_failure_ref"),
        "broker_decision_ref": latest_receipt.get("broker_decision_ref"),
        "artifact_refs": latest_receipt.get("artifact_refs") or [],
        "output_quality_ref": latest_receipt.get("output_quality_ref"),
        "replay_status": "local_read_only",
        "freshness_status": FreshnessStatus.FRESH.value if tdir.is_dir() else FreshnessStatus.MISSING.value,
        "source_refs": [str(tdir)],
        "source_ref_count": 1,
        "generated_at": latest_receipt.get("created_at"),
        "expires_at": None,
        "verdict": "GREEN_TURN_TRACE_READY" if receipt_files else "YELLOW_TURN_TRACE_EMPTY",
        "truth_state": "GREEN_TURN_TRACE_READY" if receipt_files else "YELLOW_TURN_TRACE_EMPTY",
        "data_tier": "FIXTURE" if ctx.offline_fixture else "LIVE",
    }
    state = ExcitonPanelState.GREEN if receipt_files else ExcitonPanelState.YELLOW
    if not tdir.is_dir():
        state = ExcitonPanelState.RED
    return _panel("AgentZeroTurnTracePanel", state, fields)


def _build_artifact_quality_panel(ctx: CollectorContext) -> Any:
    run_id = _discover_run_id()
    if not run_id:
        return _panel(
            "AgentZeroArtifactQualityPanel",
            ExcitonPanelState.RED,
            {
                "freshness_status": FreshnessStatus.MISSING.value,
                "source_refs": [],
                "verdict": "RED_ARTIFACT_QUALITY_SOURCE_MISSING",
                "truth_state": "RED_ARTIFACT_QUALITY_SOURCE_MISSING",
            },
            degraded_reason="no artifact store",
        )

    store = ArtifactStore(run_id)
    candidates = store.list_candidates()
    previews = []
    for cand in candidates[:5]:
        try:
            art = store.read_artifact(cand["artifact_ref"])
            qpath = store.quality_dir / f"{cand['quality_receipt_ref']}.json"
            quality = json.loads(qpath.read_text(encoding="utf-8")) if qpath.is_file() else {}
            previews.append({
                "candidate_ref": cand["candidate_id"],
                "artifact_hash": art.get("hash"),
                "body_preview": art.get("body_preview"),
                "quality_verdict": quality.get("verdict"),
                "quality_checks": quality.get("checks_run"),
                "source_refs": art.get("source_refs"),
                "provider_receipt_refs": art.get("provider_receipt_refs"),
                "failure_reasons": quality.get("reasons") if not str(quality.get("verdict", "")).startswith("GREEN_") else [],
            })
        except Exception:
            continue

    manifest = store.manifest_path
    freshness = FreshnessStatus.FRESH.value if manifest.is_file() else FreshnessStatus.MISSING.value
    verdict = "GREEN_ARTIFACT_QUALITY_READY" if previews else "YELLOW_ARTIFACT_QUALITY_EMPTY"
    state = ExcitonPanelState.GREEN if previews else ExcitonPanelState.YELLOW
    if not manifest.is_file():
        state = ExcitonPanelState.RED
        verdict = "RED_ARTIFACT_QUALITY_SOURCE_MISSING"

    fields = {
        "run_id": run_id,
        "artifact_count": len(previews),
        "artifacts_preview": previews,
        "freshness_status": freshness,
        "source_refs": [str(store.root)],
        "source_ref_count": 1,
        "generated_at": None,
        "expires_at": None,
        "verdict": verdict,
        "truth_state": verdict,
        "data_tier": "FIXTURE" if ctx.offline_fixture else "LIVE",
    }
    return _panel("AgentZeroArtifactQualityPanel", state, fields)


def build_agent_zero_review_panels(ctx: CollectorContext) -> list:
    return [
        _build_review_queue_panel(ctx),
        _build_turn_trace_panel(ctx),
        _build_artifact_quality_panel(ctx),
    ]


def build_agent_zero_review_snapshot_fields(ctx: CollectorContext) -> dict[str, Any]:
    panels = build_agent_zero_review_panels(ctx)
    out: dict[str, Any] = {}
    mapping = {
        "AgentZeroReviewQueuePanel": "agent_zero_review_queue",
        "AgentZeroTurnTracePanel": "agent_zero_turn_trace",
        "AgentZeroArtifactQualityPanel": "agent_zero_artifact_quality",
    }
    for panel in panels:
        key = mapping.get(panel.panel_id)
        if not key:
            continue
        fields = dict(panel.fields)
        out[key] = {
            "truth_state": fields.get("truth_state"),
            "freshness_status": fields.get("freshness_status"),
            "source_refs": fields.get("source_refs", []),
            "generated_at": fields.get("generated_at"),
            "expires_at": fields.get("expires_at"),
            "verdict": fields.get("verdict"),
            "panel_state": panel.state.value,
            "fields": fields,
        }
    return out


__all__ = ["build_agent_zero_review_panels", "build_agent_zero_review_snapshot_fields"]
