"""Canonical cron payload kind=dag (F6). Realtime scheduler uses realtime_schedule.json; this is the schema."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


DAG_PAYLOAD_KIND = "dag"


@dataclass(frozen=True)
class DagCronPayload:
    job_id: str
    inputs: dict[str, str] = field(default_factory=dict)
    timeout_seconds: int = 900

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "kind": DAG_PAYLOAD_KIND,
            "job_id": self.job_id,
        }
        if self.inputs:
            out["inputs"] = dict(self.inputs)
        if self.timeout_seconds != 900:
            out["timeoutSeconds"] = self.timeout_seconds
        return out


def build_dag_payload(job_id: str, inputs: dict[str, str] | None = None, *, timeout_seconds: int = 900) -> dict[str, Any]:
    return DagCronPayload(job_id=job_id, inputs=inputs or {}, timeout_seconds=timeout_seconds).to_dict()


def parse_dag_payload(raw: dict[str, Any] | None) -> DagCronPayload | None:
    if not isinstance(raw, dict):
        return None
    kind = str(raw.get("kind") or "").strip().lower()
    if kind != DAG_PAYLOAD_KIND:
        return None
    job_id = str(raw.get("job_id") or raw.get("jobId") or "").strip()
    if not job_id:
        return None
    inputs_raw = raw.get("inputs") if isinstance(raw.get("inputs"), dict) else {}
    inputs = {str(k): str(v) for k, v in inputs_raw.items() if str(k).strip() and str(v).strip()}
    timeout = int(raw.get("timeoutSeconds") or raw.get("timeout_seconds") or 900)
    return DagCronPayload(job_id=job_id, inputs=inputs, timeout_seconds=max(30, timeout))
