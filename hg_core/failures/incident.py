"""Incident model — open, attach, close, export (CT-05)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from hg_core.failures.registry import ReasonCodeRegistry, load_registry, terminal_outcome_from_reason, validate_reason_code


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Incident:
    incident_id: str
    opened_at: str
    trigger_reason_code: str
    trigger_state: str
    attached_codes: list[str] = field(default_factory=list)
    closed_at: str | None = None
    closed_by: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "opened_at": self.opened_at,
            "trigger_reason_code": self.trigger_reason_code,
            "trigger_state": self.trigger_state,
            "attached_codes": list(self.attached_codes),
            "closed_at": self.closed_at,
            "closed_by": self.closed_by,
            "status": "closed" if self.closed_at else "open",
        }


class IncidentLedger:
    def __init__(self, registry: ReasonCodeRegistry | None = None) -> None:
        self._registry = registry or load_registry()
        self._incidents: dict[str, Incident] = {}
        self._open_id: str | None = None

    def open_incident(self, reason_code: str) -> Incident:
        result = validate_reason_code(reason_code, registry=self._registry)
        if not result.ok or result.record is None:
            raise ValueError(result.reason)
        if result.record.state not in self._registry.incident_triggers:
            raise ValueError("incident_trigger_not_qualifying")
        incident_id = f"inc-{uuid.uuid4().hex[:12]}"
        incident = Incident(
            incident_id=incident_id,
            opened_at=_utc_now(),
            trigger_reason_code=result.record.code,
            trigger_state=result.record.state,
            attached_codes=[result.record.code],
        )
        self._incidents[incident_id] = incident
        self._open_id = incident_id
        return incident

    def attach(self, incident_id: str, reason_code: str) -> None:
        incident = self._incidents.get(incident_id)
        if incident is None:
            raise ValueError("incident_not_found")
        if incident.closed_at:
            raise ValueError("incident_already_closed")
        canonical = terminal_outcome_from_reason(reason_code, registry=self._registry).reason_code
        if canonical not in incident.attached_codes:
            incident.attached_codes.append(canonical)

    def close(self, incident_id: str, *, operator_id: str) -> Incident:
        from hg_core.iam.authority import validate_operator_authority

        authority = validate_operator_authority(operator_id, scope="audit_read", checkpoint="incident_close")
        if not authority.ok:
            raise ValueError(authority.reason_code)
        incident = self._incidents.get(incident_id)
        if incident is None:
            raise ValueError("incident_not_found")
        if incident.closed_at:
            raise ValueError("incident_already_closed")
        incident.closed_at = _utc_now()
        incident.closed_by = authority.resolved_operator_id or operator_id
        if self._open_id == incident_id:
            self._open_id = None
        return incident

    def export_bundle(self, incident_id: str) -> dict[str, Any]:
        incident = self._incidents.get(incident_id)
        if incident is None:
            raise ValueError("incident_not_found")
        return {
            "schema": "ftx_incident_export_v1",
            "incident": incident.to_payload(),
            "registry_hash": self._registry.registry_hash,
        }


__all__ = ["Incident", "IncidentLedger"]
