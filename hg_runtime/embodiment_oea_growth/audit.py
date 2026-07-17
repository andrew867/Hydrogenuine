"""EOG passive embodiment/OEA growth audit — slice 2, no live hardware."""

from __future__ import annotations

from typing import Any

from hg_core.embodiment_oea_cluster.errors import EOG_GROWTH_RISK_CONTAINED
from hg_core.embodiment_oea_cluster.no_authority import advisory_only_marker
from hg_runtime.embodiment_oea_growth.classifier import build_growth_assessment, classify_growth_risk
from hg_runtime.embodiment_oea_growth.fixtures import load_fixture_bundles
from hg_runtime.embodiment_oea_growth.types import FIXTURE_CLOCK, integration_from_fixture


def audit_embodiment_growth_claims(
    integrations: list[dict[str, Any]] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Passive audit of embodiment/OEA growth claims — observation only."""
    source = integrations if integrations is not None else [b["integration"] for b in load_fixture_bundles()]
    audited: list[dict[str, object]] = []
    contained_count = 0
    for row in source:
        descriptor = integration_from_fixture(row)
        risk = classify_growth_risk(descriptor)
        assessment = build_growth_assessment(descriptor, observed_at=observed_at)
        if risk != "none":
            contained_count += 1
        audited.append(
            {
                "integration_id": descriptor.integration_id,
                "platform": descriptor.platform,
                "growth_risk": risk,
                "record_hash": descriptor.record_hash,
                "audit_only": True,
                "permission_granted": False,
                "assessment_hash": assessment.record_hash,
            }
        )
    return {
        **advisory_only_marker(),
        "status": "audited",
        "reason_code": EOG_GROWTH_RISK_CONTAINED,
        "passive_audit_only": True,
        "observed_at": observed_at,
        "event_count": len(audited),
        "contained_risk_count": contained_count,
        "audited_integrations": audited,
        "live_hardware_dispatch": False,
        "permission_granted": False,
    }


__all__ = ["audit_embodiment_growth_claims"]
