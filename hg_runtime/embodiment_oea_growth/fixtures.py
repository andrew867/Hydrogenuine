"""Embodiment / OEA growth deterministic fixtures — static only."""

from __future__ import annotations

from typing import Any

from hg_runtime.embodiment_oea_growth.types import FIXTURE_CLOCK


def bundle_from_parts(
    *,
    bundle_id: str,
    integration_fixture: dict[str, str],
    growth_fixture: dict[str, str],
    notes: str = "",
) -> dict[str, Any]:
    return {
        "bundle_id": bundle_id,
        "integration": integration_fixture,
        "growth": growth_fixture,
        "notes": notes,
        "fixture_only": True,
        "observed_at": FIXTURE_CLOCK,
    }


def load_fixture_bundles() -> list[dict[str, Any]]:
    return [
        bundle_from_parts(
            bundle_id="eog-android-body-fixture",
            integration_fixture={
                "integration_id": "eog-int-android",
                "platform": "android",
                "title": "Android body integration fixture",
                "hardware_scope_real": "false",
                "pro_body_state_ref": "pro:android-fixture",
                "limitation_notice": "embodiment is not consent",
            },
            growth_fixture={
                "growth_request_id": "eog-grow-android-observe",
                "growth_kind": "observe_body_state",
                "integration_ref": "eog:eog-int-android",
            },
        ),
        bundle_from_parts(
            bundle_id="eog-robotics-arm-fixture",
            integration_fixture={
                "integration_id": "eog-int-robotics",
                "platform": "robotics",
                "title": "Robotics arm integration fixture",
                "actuator_refs": "actuator:arm-fixture",
                "hardware_scope_real": "false",
                "limitation_notice": "reach is not actuation permission",
            },
            growth_fixture={
                "growth_request_id": "eog-grow-robotics-link",
                "growth_kind": "link_pro_body_state",
                "integration_ref": "eog:eog-int-robotics",
            },
        ),
        bundle_from_parts(
            bundle_id="eog-pro-body-linked",
            integration_fixture={
                "integration_id": "eog-int-pro",
                "platform": "fixture",
                "title": "PRO body state linked fixture",
                "hardware_scope_real": "false",
                "pro_body_state_ref": "pro:body-state-fixture",
            },
            growth_fixture={
                "growth_request_id": "eog-grow-pro-link",
                "growth_kind": "link_pro_body_state",
                "integration_ref": "eog:eog-int-pro",
            },
        ),
        bundle_from_parts(
            bundle_id="eog-embodiment-consent-claim",
            integration_fixture={
                "integration_id": "eog-int-consent",
                "platform": "android",
                "title": "Embodiment presence implies consent panel",
                "hardware_scope_real": "false",
            },
            growth_fixture={
                "growth_request_id": "eog-grow-consent",
                "growth_kind": "observe_body_state",
                "integration_ref": "eog:eog-int-consent",
            },
        ),
        bundle_from_parts(
            bundle_id="eog-hardware-reach-actuation",
            integration_fixture={
                "integration_id": "eog-int-reach",
                "platform": "robotics",
                "title": "Sensor reach implies execute panel",
                "actuator_refs": "actuator:reach-fixture",
                "hardware_scope_real": "false",
            },
            growth_fixture={
                "growth_request_id": "eog-grow-reach",
                "growth_kind": "observe_body_state",
                "integration_ref": "eog:eog-int-reach",
            },
        ),
        bundle_from_parts(
            bundle_id="eog-oea-catalog-bypass",
            integration_fixture={
                "integration_id": "eog-int-oea-bypass",
                "platform": "fixture",
                "title": "Skip GPP UEAK direct OEA catalog panel",
                "hardware_scope_real": "false",
            },
            growth_fixture={
                "growth_request_id": "eog-grow-oea-bypass",
                "growth_kind": "observe_body_state",
                "integration_ref": "eog:eog-int-oea-bypass",
            },
        ),
        bundle_from_parts(
            bundle_id="eog-hardware-not-real",
            integration_fixture={
                "integration_id": "eog-int-hardware-real",
                "platform": "android",
                "title": "Real hardware android scope",
                "hardware_scope_real": "true",
                "pro_body_state_ref": "pro:hardware-android",
            },
            growth_fixture={
                "growth_request_id": "eog-grow-hardware",
                "growth_kind": "android_integration",
                "target_hash": "sha256:android-target",
                "integration_ref": "eog:eog-int-hardware-real",
            },
        ),
        bundle_from_parts(
            bundle_id="eog-stale-growth-request",
            integration_fixture={
                "integration_id": "eog-int-stale",
                "platform": "fixture",
                "title": "Stale growth request fixture",
                "hardware_scope_real": "false",
            },
            growth_fixture={
                "growth_request_id": "eog-grow-stale",
                "growth_kind": "catalog_entry_proposal",
                "target_hash": "sha256:catalog-target",
                "expires_at": "2026-06-13T00:00:00.000000Z",
                "integration_ref": "eog:eog-int-stale",
            },
        ),
        bundle_from_parts(
            bundle_id="eog-oea-growth-proposal",
            integration_fixture={
                "integration_id": "eog-int-catalog",
                "platform": "fixture",
                "title": "Bounded OEA catalog growth proposal",
                "hardware_scope_real": "false",
            },
            growth_fixture={
                "growth_request_id": "eog-grow-catalog",
                "growth_kind": "catalog_entry_proposal",
                "target_hash": "sha256:catalog-entry-target",
                "integration_ref": "eog:eog-int-catalog",
            },
        ),
    ]


def load_pro_body_fixtures() -> list[dict[str, str]]:
    return [
        {
            "body_state_id": "pro-body-android-fixture",
            "platform_ref": "fixture:android",
            "contact_state": "none",
            "confidence": "low",
            "event_head": "sha256:pro-event-head-android",
        },
        {
            "body_state_id": "pro-body-robotics-fixture",
            "platform_ref": "fixture:robotics",
            "actuator_refs": "actuator:arm-fixture",
            "contact_state": "none",
            "confidence": "low",
            "event_head": "sha256:pro-event-head-robotics",
        },
    ]


def load_oea_catalog_fixtures() -> list[dict[str, str]]:
    return [
        {
            "catalog_entry_id": "oea-cat-observe-only",
            "capability_label": "Observe body sensors read-only",
            "bounded_by_gpp_ueak": "true",
            "soar_review_required": "true",
        },
        {
            "catalog_entry_id": "oea-cat-android-bridge",
            "capability_label": "Android sensor bridge proposal",
            "bounded_by_gpp_ueak": "true",
            "soar_review_required": "true",
        },
        {
            "catalog_entry_id": "oea-cat-robotics-arm",
            "capability_label": "Robotics arm telemetry proposal",
            "bounded_by_gpp_ueak": "true",
            "soar_review_required": "true",
        },
        {
            "catalog_entry_id": "oea-cat-actuation-candidate",
            "capability_label": "Actuation candidate requires authority chain",
            "bounded_by_gpp_ueak": "true",
            "soar_review_required": "true",
        },
        {
            "catalog_entry_id": "oea-cat-bounded-growth",
            "capability_label": "Catalog growth bounded by GPP UEAK SOAR",
            "bounded_by_gpp_ueak": "true",
            "soar_review_required": "true",
        },
    ]


__all__ = [
    "bundle_from_parts",
    "load_fixture_bundles",
    "load_oea_catalog_fixtures",
    "load_pro_body_fixtures",
]
