"""EXCITON Phase 0 data sources — best-effort, read-only collectors.

One collector per panel. Each returns an ``ExcitonPanelStatus`` whose ``fields`` are
already scrubbed of forbidden data. A collector that cannot reach its subsystem returns a
``DEGRADED`` panel with a plain-English reason — honest, never fake-green, never a crash.

Two modes:
- ``offline_fixture=True`` → deterministic canned data (for tests / dev fixtures). The
  temporal panel uses fixed values so two builds hash identically.
- ``offline_fixture=False`` → live best-effort probes (CHRONO is read for real; every other
  subsystem is probed defensively and degrades on any error).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from hg_runtime.exciton.live_probes import LIVE_PROBE_DISPATCH, set_probe_context
from hg_runtime.exciton.panel_registry import CONTRACT_BY_ID, REQUIRED_PANELS, scrub_fields
from hg_runtime.exciton.schema import (
    FIXTURE_UTC,
    ExcitonDegradedState,
    ExcitonPanelState,
    ExcitonPanelStatus,
    ExcitonProofLink,
)


WORKSPACE = Path(__file__).resolve().parents[2]


@dataclass
class CollectorContext:
    offline_fixture: bool = False
    allow_network: bool = False


def _panel(
    panel_id: str,
    state: ExcitonPanelState,
    fields: dict[str, Any],
    *,
    proof_links: list[ExcitonProofLink] | None = None,
    degraded_reason: str | None = None,
) -> ExcitonPanelStatus:
    contract = CONTRACT_BY_ID[panel_id]
    clean, _removed = scrub_fields(fields)
    if "data_tier" not in clean:
        clean = {**clean, "data_tier": "LIVE"}
    degraded = None
    if state in (ExcitonPanelState.DEGRADED, ExcitonPanelState.UNKNOWN):
        degraded = ExcitonDegradedState(True, degraded_reason or contract.degraded_reason)
    return ExcitonPanelStatus(
        panel_id=panel_id,
        title=contract.title,
        source=contract.source,
        state=state,
        fields=clean,
        proof_links=proof_links or [],
        degraded=degraded,
    )


def _degraded(panel_id: str, reason: str) -> ExcitonPanelStatus:
    return _panel(panel_id, ExcitonPanelState.DEGRADED, {}, degraded_reason=reason)


# --- Temporal (CHRONO) — the one collector wired to a real subsystem in live mode. -------

def _collect_temporal(ctx: CollectorContext) -> ExcitonPanelStatus:
    if ctx.offline_fixture:
        return _panel(
            "TemporalPanel",
            ExcitonPanelState.GREEN,
            {
                "current_time": FIXTURE_UTC,
                "chrono_ref": "sha256:fixture-epoch-lock",
                "lock_state": "LOCKED",
                "boot_epoch": "exciton-fixture-epoch",
                "time_confidence": "FIXTURE",
                "time_uncertain": False,
            },
        )
    set_probe_context(allow_network=ctx.allow_network)
    state, fields = LIVE_PROBE_DISPATCH["TemporalPanel"]()
    return _panel("TemporalPanel", state, fields)


# --- Fixture canned data for the remaining panels (deterministic). -----------------------

_FIXTURE_PANELS: dict[str, tuple[ExcitonPanelState, dict[str, Any]]] = {
    "OverviewPanel": (
        ExcitonPanelState.GREEN,
        {
            "identity": {"long_name": "Agent Zero", "short_name": "Zero", "ui": "A#0", "code_id": "agent0"},
            "boot_id": "exciton-fixture-boot",
            "run_id": "exciton-fixture-run",
            "overall_verdict": "GREEN_EXCITON_STATUS_OK",
            "dangerous_actions_disabled": True,
        },
    ),
    "WakeRefreshPanel": (ExcitonPanelState.GREEN, {"wake_status": "AWAKE", "last_reconcile": FIXTURE_UTC}),
    "ExternalAnchorPanel": (
        ExcitonPanelState.GREEN,
        {"anchor_present": True, "signed_status": "SIGNED", "witness_ref": "ewj:fixture"},
    ),
    "WitnessJournalPanel": (
        ExcitonPanelState.GREEN,
        {"latest_event_meta": {"kind": "WAKE", "at": FIXTURE_UTC}, "chain_status": "INTACT", "chain_length": 3},
    ),
    "SelfMirrorPanel": (ExcitonPanelState.GREEN, {"summary": "continuity intact", "continuity_status": "OK"}),
    "WillPanel": (ExcitonPanelState.GREEN, {"summary": "advisory only", "advisory_hypotheses_count": 0}),
    "TrustBoundaryPanel": (ExcitonPanelState.GREEN, {"status": "GREEN_TRUST_BOUNDARY_HELD", "quarantine_count": 0}),
    "PowerBoundaryPanel": (
        ExcitonPanelState.GREEN,
        {"opb_state": "BOUNDED", "ipb_state": "BOUNDED", "silence_state": "OK", "mission_state": "OK", "resource_state": "OK"},
    ),
    "StorageProofPanel": (ExcitonPanelState.GREEN, {"storage_verdict": "GREEN", "proof_count": 1}),
    "ProviderPanel": (
        ExcitonPanelState.GREEN,
        {"provider_status": "LOCAL_READY", "openvino_present": True, "cloud_disabled": True},
    ),
    "ToolCapabilityPanel": (
        ExcitonPanelState.GREEN,
        {"capabilities": ["status_read", "proof_read"], "dangerous_actions_disabled": True},
    ),
    "OrganPanel": (ExcitonPanelState.GREEN, {"organ_ids": ["AIO"], "heartbeats": {"AIO": "OK"}, "states": {"AIO": "READY"}}),
    "AudioPanel": (
        ExcitonPanelState.DEGRADED,
        {
            "capture_mode": "OFF",
            "stt_verdict": "STT_MODEL_MISSING",
            "tts_verdict": "TTS_DEP_MISSING",
            "live_mic_enabled": False,
            "playback_enabled": False,
        },
    ),
    "WeatherVoicePanel": (
        ExcitonPanelState.GREEN,
        {"source": "fixture-weather", "retrieved_time": FIXTURE_UTC, "artifact_hash": "sha256:fixture", "char_count": 48},
    ),
    "ProofBundlePanel": (
        ExcitonPanelState.GREEN,
        {"stage_a": "present", "stage_b": "present", "stage_c": "present", "bundles": 3},
    ),
    "QueuePanel": (ExcitonPanelState.GREEN, {"outstanding_requests": []}),
    "StopPanicPanel": (
        ExcitonPanelState.GREEN,
        {"stop_available": True, "panic_available": True, "stop_state": "READY"},
    ),
    "OperatorNotesPanel": (ExcitonPanelState.GREEN, {"notes": []}),
}


def _collect_fixture(panel_id: str) -> ExcitonPanelStatus:
    state, fields = _FIXTURE_PANELS[panel_id]
    fields = {**fields, "data_tier": "FIXTURE"}
    reason = "audio deps not installed" if panel_id == "AudioPanel" else None
    return _panel(panel_id, state, fields, degraded_reason=reason)


# --- Live best-effort probes for non-temporal panels. ------------------------------------

def _collect_live(panel_id: str) -> ExcitonPanelStatus:
    """Conservative live probe: report real subsystem status or degrade honestly."""
    live_probe = LIVE_PROBE_DISPATCH.get(panel_id)
    if not live_probe:
        return _degraded(panel_id, "no live probe registered")
    try:
        state, fields = live_probe()
        return _panel(panel_id, state, fields)
    except Exception as exc:  # pragma: no cover
        return _degraded(panel_id, f"live probe failed: {type(exc).__name__}")


def build_panels(ctx: CollectorContext) -> list[ExcitonPanelStatus]:
    set_probe_context(allow_network=ctx.allow_network)
    panels: list[ExcitonPanelStatus] = []
    for panel_id in REQUIRED_PANELS:
        if panel_id == "TemporalPanel":
            panels.append(_collect_temporal(ctx))
        elif ctx.offline_fixture:
            panels.append(_collect_fixture(panel_id))
        else:
            panels.append(_collect_live(panel_id))
    return panels


COLLECTORS: dict[str, Callable[[CollectorContext], ExcitonPanelStatus]] = {
    "TemporalPanel": _collect_temporal,
}


__all__ = ["COLLECTORS", "CollectorContext", "build_panels"]
