"""Field run incident summary."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.overnight_field_run.schema import field_run_dir, new_id, now_iso


@dataclass
class FieldRunIncidentSummary:
    incident_summary_id: str
    field_run_id: str
    incidents: list[str] = field(default_factory=list)
    panic_events: int = 0
    stop_events: int = 0
    provider_degraded: bool = False
    live_read_degraded: bool = False
    authority_expansion_attempts: int = 0
    created_at: str = ""
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "incident_summary_id": self.incident_summary_id,
            "field_run_id": self.field_run_id,
            "incidents": self.incidents,
            "panic_events": self.panic_events,
            "stop_events": self.stop_events,
            "provider_degraded": self.provider_degraded,
            "live_read_degraded": self.live_read_degraded,
            "authority_expansion_attempts": self.authority_expansion_attempts,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> FieldRunIncidentSummary:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return FieldRunIncidentSummary(**{**self.__dict__, "hash": compute_record_hash(body)})


def write_incident_summary(summary: FieldRunIncidentSummary, *, base: Path | None = None) -> Path:
    root = field_run_dir(summary.field_run_id, base=base)
    root.mkdir(parents=True, exist_ok=True)
    path = root / "incident_summary.json"
    path.write_text(json.dumps(summary.with_hash().to_payload(), indent=2) + "\n", encoding="utf-8")
    return path


def build_incident_summary(
    field_run_id: str,
    *,
    incidents: list[str],
    panic_requested: bool,
    stop_requested: bool,
    session_verdict: str,
    base: Path | None = None,
) -> FieldRunIncidentSummary:
    summary = FieldRunIncidentSummary(
        incident_summary_id=new_id("incident"),
        field_run_id=field_run_id,
        incidents=incidents,
        panic_events=1 if panic_requested else 0,
        stop_events=1 if stop_requested else 0,
        provider_degraded="PROVIDER_UNAVAILABLE" in session_verdict,
        live_read_degraded="LIVE_READ" in session_verdict,
        authority_expansion_attempts=0,
        created_at=now_iso(),
    ).with_hash()
    write_incident_summary(summary, base=base)
    return summary
