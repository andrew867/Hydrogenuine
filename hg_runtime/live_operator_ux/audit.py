"""OUX-LIVE audit log — passive operator UX event recording."""

from __future__ import annotations

from typing import Any

from hg_core.oux_live.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.live_operator_ux.fixtures import load_oux_fixtures
from hg_runtime.live_operator_ux.types import FIXTURE_CLOCK, OperatorUXAuditRecord


def _audit_id(action_ref: str, event_code: str) -> str:
    digest = canonical_hash({"action_ref": action_ref, "event_code": event_code})
    return f"oux-audit-{digest.rsplit(':', 1)[-1][:12]}"


def record_audit_event(
    *,
    action_ref: str,
    operator_ref: str | None,
    event_code: str,
    observed_at: str = FIXTURE_CLOCK,
) -> OperatorUXAuditRecord:
    return OperatorUXAuditRecord(
        audit_id=_audit_id(action_ref, event_code),
        action_ref=action_ref,
        operator_ref=operator_ref,
        observed_at=observed_at,
        event_code=event_code,
    )


def audit_operator_ux_events(*, observed_at: str = FIXTURE_CLOCK) -> dict[str, Any]:
    """Passive audit of fixture bundles — audit log only, not authority."""
    bundles = load_oux_fixtures()
    records: list[dict[str, Any]] = []
    for bundle in bundles:
        req = bundle.get("action_request", {})
        request_id = str(req.get("request_id", bundle["bundle_id"]))
        event_code = f"OUX_FIXTURE_{bundle['bundle_id'].upper().replace('-', '_')}"
        record = record_audit_event(
            action_ref=request_id,
            operator_ref=req.get("operator_ref"),
            event_code=event_code,
            observed_at=observed_at,
        )
        records.append(record.to_payload())

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "oux.advisory.audit_complete",
        "passive_audit_only": True,
        "event_count": len(records),
        "records": records,
        "observed_at": observed_at,
    }


__all__ = ["audit_operator_ux_events", "record_audit_event"]
