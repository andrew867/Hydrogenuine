"""Redacted incident export packages."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_runtime.openvino_watchtower.index import build_timeline_from_events
from hg_runtime.openvino_watchtower.organ_trace import build_organ_trace
from hg_runtime.openvino_watchtower.performance_budget import evaluate_snapshot
from hg_runtime.openvino_watchtower.redaction import redact_payload
from hg_runtime.openvino_watchtower.replay import WatchtowerReplay
from hg_runtime.openvino_watchtower.schema import TelemetryRedactionPolicy
from hg_runtime.openvino_watchtower.session import load_session
from hg_runtime.openvino_watchtower.waterfall import build_waterfall

WORKSPACE = Path(__file__).resolve().parents[2]
INCIDENTS_ROOT = WORKSPACE / "docs/proofs/openvino_watchtower/incidents"

_SECRET_RE = re.compile(r"(?i)(api[_-]?key|secret|password|token|bearer|private[_-]?key)")


def _scan_secrets(text: str) -> list[str]:
    return _SECRET_RE.findall(text)


def export_incident(
    *,
    session_id: str,
    incident_id: str,
    reason: str,
    snapshot: dict[str, Any] | None = None,
) -> Path:
    out = INCIDENTS_ROOT / incident_id
    out.mkdir(parents=True, exist_ok=True)

    replay = WatchtowerReplay.open(session_id)
    events = replay.events()
    snap = snapshot or replay.snapshot() or {}
    red_snap, _ = redact_payload(snap, policy=TelemetryRedactionPolicy())
    red_events = []
    for ev in events:
        r, _ = redact_payload(ev, policy=TelemetryRedactionPolicy())
        red_events.append(r)

    trace = build_organ_trace(red_events, snapshot=red_snap)
    waterfall = build_waterfall(red_snap, red_events)
    perf = evaluate_snapshot(red_snap)

    manifest = {
        "incident_id": incident_id,
        "session_id": session_id,
        "reason": reason,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "event_count": len(red_events),
        "snapshot_hash": hashlib.sha256(json.dumps(red_snap, sort_keys=True).encode()).hexdigest(),
        "authority_created": False,
        "permission_granted": False,
    }

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    with (out / "redacted_events.jsonl").open("w", encoding="utf-8") as fh:
        for ev in red_events:
            fh.write(json.dumps(ev, sort_keys=True) + "\n")
    (out / "redacted_snapshot.json").write_text(json.dumps(red_snap, indent=2), encoding="utf-8")
    (out / "organ_trace.json").write_text(json.dumps(trace, indent=2), encoding="utf-8")
    (out / "waterfall.json").write_text(json.dumps(waterfall, indent=2), encoding="utf-8")
    (out / "performance_budget.json").write_text(json.dumps(perf, indent=2), encoding="utf-8")

    privacy_hits = _scan_secrets(json.dumps(red_events + [red_snap]))
    privacy_report = {
        "raw_prompts_enabled": False,
        "hidden_cot_enabled": False,
        "secret_pattern_hits": privacy_hits,
        "redaction_applied": True,
    }
    (out / "privacy_report.json").write_text(json.dumps(privacy_report, indent=2), encoding="utf-8")

    summary = f"# Incident {incident_id}\n\nReason: {reason}\nSession: {session_id}\nEvents: {len(red_events)}\nPerf: {perf.get('verdict')}\n"
    (out / "summary.md").write_text(summary, encoding="utf-8")
    (out / "privacy_report.md").write_text(
        "# Privacy Report\n\nRedaction applied. Raw prompts and CoT disabled.\n", encoding="utf-8"
    )
    return out


__all__ = ["INCIDENTS_ROOT", "export_incident"]
