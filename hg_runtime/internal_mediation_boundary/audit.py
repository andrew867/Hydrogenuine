"""IMB passive conflict-event audit — slice 2, no live mediation."""

from __future__ import annotations

from typing import Any

from hg_core.imb_cluster.errors import IMB_CONFLICT_DETECTED
from hg_core.imb_cluster.no_authority import advisory_only_marker
from hg_runtime.internal_mediation_boundary.detector import detect_internal_conflicts
from hg_runtime.internal_mediation_boundary.fixtures import claims_from_bundle, load_fixture_bundles
from hg_runtime.internal_mediation_boundary.types import FIXTURE_CLOCK, module_claim_from_fixture


def audit_conflict_events(
    events: list[dict[str, Any]] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Passive audit of conflict-like fixture events — observation only."""
    if events is None:
        rows: list[dict[str, Any]] = []
        for bundle in load_fixture_bundles():
            for claim in bundle.get("claims", []):
                rows.append(
                    {
                        "event_id": claim.get("claim_id", "imb-audit-unknown"),
                        "source_module": claim.get("source_module", "unknown"),
                        "claim_type": claim.get("claim_type", "unknown"),
                        "summary": claim.get("claim_summary", "audit fixture event"),
                    }
                )
    else:
        rows = list(events)

    audited: list[dict[str, object]] = []
    contained_count = 0
    for row in rows:
        claim = module_claim_from_fixture(
            {
                "claim_id": str(row.get("event_id", row.get("claim_id", "imb-audit-unknown"))),
                "source_module": str(row.get("source_module", "unknown")),
                "claim_type": str(row.get("claim_type", "unknown")),
                "claim_summary": str(row.get("summary", row.get("claim_summary", "audit fixture event"))),
            }
        )
        detection = detect_internal_conflicts((claim,), detected_at=observed_at)
        conflict_count = int(detection.get("conflict_count", 0))
        if claim.source_module == "unknown" or conflict_count == 0:
            contained_count += 1
        audited.append(
            {
                "claim_id": claim.claim_id,
                "source_module": claim.source_module,
                "claim_type": claim.claim_type,
                "conflict_count": conflict_count,
                "record_hash": claim.record_hash,
                "audit_only": True,
                "permission_granted": False,
            }
        )

    return {
        **advisory_only_marker(),
        "status": "audited",
        "reason_code": IMB_CONFLICT_DETECTED,
        "passive_audit_only": True,
        "observed_at": observed_at,
        "event_count": len(audited),
        "contained_count": contained_count,
        "audited_events": audited,
        "live_mediation_dispatch": False,
        "permission_granted": False,
    }


__all__ = ["audit_conflict_events"]
