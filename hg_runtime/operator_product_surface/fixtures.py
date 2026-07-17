"""Operator product surface deterministic fixtures — static only."""

from __future__ import annotations

from typing import Any

from hg_runtime.operator_product_surface.types import FIXTURE_CLOCK


def bundle_from_parts(
    *,
    bundle_id: str,
    surface_fixture: dict[str, str],
    action_fixture: dict[str, str],
    notes: str = "",
) -> dict[str, Any]:
    return {
        "bundle_id": bundle_id,
        "surface": surface_fixture,
        "action": action_fixture,
        "notes": notes,
        "fixture_only": True,
        "observed_at": FIXTURE_CLOCK,
    }


def load_fixture_bundles() -> list[dict[str, Any]]:
    return [
        bundle_from_parts(
            bundle_id="ops-exciton-observe-pulse",
            surface_fixture={
                "surface_descriptor_id": "ops-surf-exciton-pulse",
                "surface": "exciton",
                "title": "Runtime pulse viewer",
                "polish_level": "mvp",
                "safety_disclaimer_visible": "true",
                "pres_trb_sil_boundaries_stable": "true",
                "limitation_notice": "polish is not safety",
            },
            action_fixture={
                "action_request_id": "ops-act-observe-pulse",
                "surface": "exciton",
                "action_kind": "observe",
                "operator_ref": "operator:fixture",
                "evidence_refs": "sha256:ops-pulse",
            },
        ),
        bundle_from_parts(
            bundle_id="ops-exciton-hash-bound-pause",
            surface_fixture={
                "surface_descriptor_id": "ops-surf-exciton-pause",
                "surface": "exciton",
                "title": "Hash-bound pause control",
                "polish_level": "mvp",
                "safety_disclaimer_visible": "true",
                "pres_trb_sil_boundaries_stable": "true",
                "hash_bound_controls_only": "true",
            },
            action_fixture={
                "action_request_id": "ops-act-pause",
                "surface": "exciton",
                "action_kind": "pause_request",
                "target_hash": "sha256:pause-target-fixture",
                "operator_ref": "operator:fixture",
            },
        ),
        bundle_from_parts(
            bundle_id="ops-exciton-stale-approval",
            surface_fixture={
                "surface_descriptor_id": "ops-surf-stale",
                "surface": "exciton",
                "title": "Stale approval fixture",
                "safety_disclaimer_visible": "true",
                "pres_trb_sil_boundaries_stable": "true",
            },
            action_fixture={
                "action_request_id": "ops-act-stale",
                "surface": "exciton",
                "action_kind": "approve_change",
                "target_hash": "sha256:approval-target",
                "expires_at": "2026-06-13T00:00:00.000000Z",
            },
        ),
        bundle_from_parts(
            bundle_id="ops-polish-safety-claim",
            surface_fixture={
                "surface_descriptor_id": "ops-surf-polish-safety",
                "surface": "exciton",
                "title": "Friendly green UI means safe cockpit",
                "polish_level": "high",
                "safety_disclaimer_visible": "false",
                "pres_trb_sil_boundaries_stable": "true",
            },
            action_fixture={
                "action_request_id": "ops-act-polish-safety",
                "surface": "exciton",
                "action_kind": "display_timeline",
            },
        ),
        bundle_from_parts(
            bundle_id="ops-embodiment-consent-claim",
            surface_fixture={
                "surface_descriptor_id": "ops-surf-embodiment",
                "surface": "exciton",
                "title": "Embodiment presence implies consent panel",
                "safety_disclaimer_visible": "true",
                "pres_trb_sil_boundaries_stable": "true",
            },
            action_fixture={
                "action_request_id": "ops-act-embodiment",
                "surface": "exciton",
                "action_kind": "observe",
            },
        ),
        bundle_from_parts(
            bundle_id="ops-hardware-reach-claim",
            surface_fixture={
                "surface_descriptor_id": "ops-surf-hardware",
                "surface": "exciton",
                "title": "Sensor reach implies execute panel",
                "safety_disclaimer_visible": "true",
                "pres_trb_sil_boundaries_stable": "true",
            },
            action_fixture={
                "action_request_id": "ops-act-hardware",
                "surface": "exciton",
                "action_kind": "observe",
            },
        ),
        bundle_from_parts(
            bundle_id="ops-oea-bypass-claim",
            surface_fixture={
                "surface_descriptor_id": "ops-surf-oea-bypass",
                "surface": "exciton",
                "title": "Skip GPP UEAK direct OEA panel",
                "safety_disclaimer_visible": "true",
                "pres_trb_sil_boundaries_stable": "true",
            },
            action_fixture={
                "action_request_id": "ops-act-oea-bypass",
                "surface": "exciton",
                "action_kind": "observe",
            },
        ),
        bundle_from_parts(
            bundle_id="ops-pres-unstable",
            surface_fixture={
                "surface_descriptor_id": "ops-surf-pres-unstable",
                "surface": "exciton",
                "title": "Surface before PRES/TRB/SIL stable",
                "safety_disclaimer_visible": "true",
                "pres_trb_sil_boundaries_stable": "false",
            },
            action_fixture={
                "action_request_id": "ops-act-pres-unstable",
                "surface": "exciton",
                "action_kind": "observe",
            },
        ),
        bundle_from_parts(
            bundle_id="ops-approve-authority-chain",
            surface_fixture={
                "surface_descriptor_id": "ops-surf-approve",
                "surface": "exciton",
                "title": "Approval UI",
                "safety_disclaimer_visible": "true",
                "pres_trb_sil_boundaries_stable": "true",
            },
            action_fixture={
                "action_request_id": "ops-act-approve",
                "surface": "exciton",
                "action_kind": "approve_change",
                "target_hash": "sha256:change-approval-target",
            },
        ),
    ]


def load_plt_surface_fixtures() -> list[dict[str, str]]:
    return [
        {
            "plt_surface_id": "plt-surf-live-events",
            "surface_name": "live_event_viewer",
            "function_label": "Tail + filter RTC bus",
            "writes_events_only": "true",
            "panic_banner_required": "true",
            "hash_mismatch_visible": "true",
            "thinking_vs_committed_distinct": "true",
            "limitation_notice": "writes emit events only",
        },
        {
            "plt_surface_id": "plt-surf-world-state",
            "surface_name": "world_state_summary",
            "function_label": "Read-only reducer snapshot",
            "writes_events_only": "true",
            "panic_banner_required": "true",
        },
        {
            "plt_surface_id": "plt-surf-pending-proposals",
            "surface_name": "pending_proposals",
            "function_label": "SRP queue with bundle hash visible",
            "writes_events_only": "true",
            "panic_banner_required": "true",
            "hash_mismatch_visible": "true",
        },
        {
            "plt_surface_id": "plt-surf-panic",
            "surface_name": "panic_button",
            "function_label": "Idempotent PANIC banner on all views",
            "writes_events_only": "true",
            "panic_banner_required": "true",
        },
        {
            "plt_surface_id": "plt-surf-approval",
            "surface_name": "approval_ui",
            "function_label": "Sign ChangeApproval with hash mismatch visible",
            "writes_events_only": "true",
            "panic_banner_required": "true",
            "hash_mismatch_visible": "true",
        },
    ]


__all__ = ["bundle_from_parts", "load_fixture_bundles", "load_plt_surface_fixtures"]
