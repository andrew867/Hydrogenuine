"""ERB passive relation-event audit — slice 2, no live external calls."""

from __future__ import annotations

from typing import Any

from hg_core.erb_cluster.errors import ERB_ENTITY_RECORDED
from hg_core.erb_cluster.no_authority import advisory_only_marker
from hg_runtime.external_relation_boundary.classifier import classify_entity_relation
from hg_runtime.external_relation_boundary.fixtures import load_fixture_bundles, relation_from_bundle
from hg_runtime.external_relation_boundary.types import FIXTURE_CLOCK, context_from_fixture, entity_from_fixture


def audit_relation_events(
    events: list[dict[str, Any]] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Passive audit of relation-like fixture events — observation only."""
    if events is None:
        rows: list[dict[str, Any]] = []
        for bundle in load_fixture_bundles():
            rows.append(
                {
                    "entity_ref_id": bundle.get("entity", {}).get("entity_ref_id", "erb-audit-unknown"),
                    "entity_type": bundle.get("entity", {}).get("entity_type", "unknown"),
                    "relation_mode": bundle.get("context", {}).get("relation_mode", "unknown"),
                    "sensitivity": bundle.get("context", {}).get("sensitivity", "unknown"),
                }
            )
    else:
        rows = list(events)

    audited: list[dict[str, object]] = []
    contained_count = 0
    for row in rows:
        entity = entity_from_fixture(
            {
                "entity_ref_id": str(row.get("entity_ref_id", "erb-audit-unknown")),
                "entity_type": str(row.get("entity_type", "unknown")),
            }
        )
        context = context_from_fixture(
            {
                "relation_context_id": str(row.get("relation_context_id", f"ctx-{entity.entity_ref_id}")),
                "relation_mode": str(row.get("relation_mode", "unknown")),
                "sensitivity": str(row.get("sensitivity", "unknown")),
            },
            entity_ref_id=entity.entity_ref_id,
        )
        classification = classify_entity_relation(entity, context)
        if entity.entity_type == "unknown" or classification.get("claim_risk") == "unknown":
            contained_count += 1
        audited.append(
            {
                "entity_ref_id": entity.entity_ref_id,
                "entity_type": entity.entity_type,
                "relation_mode": context.relation_mode,
                "claim_risk": classification.get("claim_risk"),
                "classification_is_advisory_only": classification.get("classification_is_advisory_only"),
                "record_hash": entity.record_hash,
                "audit_only": True,
                "permission_granted": False,
            }
        )

    return {
        **advisory_only_marker(),
        "status": "audited",
        "reason_code": ERB_ENTITY_RECORDED,
        "passive_audit_only": True,
        "observed_at": observed_at,
        "event_count": len(audited),
        "contained_count": contained_count,
        "audited_events": audited,
        "live_external_call": False,
        "permission_granted": False,
    }


__all__ = ["audit_relation_events"]
