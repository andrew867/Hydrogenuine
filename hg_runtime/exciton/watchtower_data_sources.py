"""EXCITON Inference Watchtower panel collector."""

from __future__ import annotations

from hg_runtime.exciton.data_sources import CollectorContext, _panel
from hg_runtime.exciton.schema import ExcitonDegradedState, ExcitonPanelState, ExcitonPanelStatus
from hg_runtime.openvino_watchtower.exciton_panel import (
    exciton_panel_fields,
    exciton_panel_state,
    load_watchtower_snapshot,
)


def _collect_inference_watchtower(ctx: CollectorContext) -> ExcitonPanelStatus:
    if ctx.offline_fixture:
        fields = {
            "data_tier": "FIXTURE",
            "provider_status": "FIXTURE",
            "provider_mode": "fixture",
            "openvino_present": True,
            "model_loaded": False,
            "freshness_verdict": "warning",
            "active_inference_count": 0,
            "organ_activity_summary": {"model_provider": "idle"},
            "redaction_active": True,
            "raw_prompt_disabled": True,
            "hidden_cot_disabled": True,
            "authority_created": False,
            "permission_granted": False,
            "advisory_only": True,
        }
        return _panel("InferenceWatchtowerPanel", ExcitonPanelState.YELLOW, fields)
    snap = load_watchtower_snapshot(prefer_api=ctx.allow_network)
    state = exciton_panel_state(snap)
    fields = exciton_panel_fields(snap)
    if state != ExcitonPanelState.GREEN:
        degraded_reason = snap.get("human_message") or "watchtower degraded or stale"
        return ExcitonPanelStatus(
            panel_id="InferenceWatchtowerPanel",
            title="Inference Watchtower",
            source="openvino_watchtower",
            state=state,
            fields=fields,
            proof_links=[],
            degraded=ExcitonDegradedState(True, degraded_reason),
        )
    return _panel("InferenceWatchtowerPanel", state, fields)


def build_inference_watchtower_panels(ctx: CollectorContext) -> list[ExcitonPanelStatus]:
    return [_collect_inference_watchtower(ctx)]


__all__ = ["build_inference_watchtower_panels"]
