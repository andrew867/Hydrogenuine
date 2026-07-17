"""EXCITON passive surface polish audit — slice 2, no live UI."""

from __future__ import annotations

from typing import Any

from hg_core.exciton_cluster.errors import EXCITON_POLISH_RISK_CONTAINED
from hg_core.exciton_cluster.no_authority import advisory_only_marker
from hg_runtime.operator_product_surface.classifier import build_polish_assessment, classify_polish_risk
from hg_runtime.operator_product_surface.fixtures import load_fixture_bundles
from hg_runtime.operator_product_surface.types import FIXTURE_CLOCK, surface_descriptor_from_fixture


def audit_surface_polish_claims(
    descriptors: list[dict[str, Any]] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Passive audit of operator surface polish claims — observation only."""
    source = descriptors if descriptors is not None else [b["surface"] for b in load_fixture_bundles()]
    audited: list[dict[str, object]] = []
    contained_count = 0
    for row in source:
        descriptor = surface_descriptor_from_fixture(row)
        risk = classify_polish_risk(descriptor)
        assessment = build_polish_assessment(descriptor, observed_at=observed_at)
        if risk != "none":
            contained_count += 1
        audited.append(
            {
                "surface_descriptor_id": descriptor.surface_descriptor_id,
                "surface": descriptor.surface,
                "polish_risk": risk,
                "record_hash": descriptor.record_hash,
                "audit_only": True,
                "permission_granted": False,
                "assessment_hash": assessment.record_hash,
            }
        )
    return {
        **advisory_only_marker(),
        "status": "audited",
        "reason_code": EXCITON_POLISH_RISK_CONTAINED,
        "passive_audit_only": True,
        "observed_at": observed_at,
        "event_count": len(audited),
        "contained_risk_count": contained_count,
        "audited_surfaces": audited,
        "live_ui_dispatch": False,
        "permission_granted": False,
    }


__all__ = ["audit_surface_polish_claims"]
