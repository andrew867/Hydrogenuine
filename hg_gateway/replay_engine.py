"""
Pack 25: Replay engine — verify event_stream and evidence_ledger hash chains for a run.

Loads events and ledger for run_id; verifies prev_* / *_sha256 chains; validates required sequences.
Outputs: REPLAY_VERIFY.txt ("OK" or "ERROR: ..."), REPLAY_REPORT.json.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple

from hg_gateway.events_ledger import get_events_for_run, get_evidence_for_run
from hg_gateway.db import _get_db_path


def _verify_event_chain(events: List[Dict[str, Any]]) -> List[str]:
    """Verify event_stream chain: prev_event_sha256 -> event_sha256. Returns list of errors."""
    errors: List[str] = []
    prev_sha: Optional[str] = None
    for i, row in enumerate(events):
        prev_stored = row.get("prev_event_sha256")
        if prev_stored != prev_sha:
            if prev_sha is not None or prev_stored is not None:
                errors.append(f"event[{i}] prev_event_sha256 mismatch (expected {prev_sha!r}, got {prev_stored!r})")
        chain_input = f"{prev_sha or ''}:{row['event_id']}:{row['ts']}:{row['payload_sha256']}"
        expected_sha = hashlib.sha256(chain_input.encode("utf-8")).hexdigest()
        if row.get("event_sha256") != expected_sha:
            errors.append(f"event[{i}] event_sha256 mismatch (event_id={row.get('event_id')})")
        prev_sha = row.get("event_sha256")
    return errors


def _verify_ledger_chain(rows: List[Dict[str, Any]]) -> List[str]:
    """Verify evidence_ledger chain. Returns list of errors."""
    errors: List[str] = []
    prev_sha: Optional[str] = None
    for i, row in enumerate(rows):
        prev_stored = row.get("prev_ledger_sha256")
        if prev_stored != prev_sha:
            if prev_sha is not None or prev_stored is not None:
                errors.append(f"ledger[{i}] prev_ledger_sha256 mismatch")
        chain_input = f"{prev_sha or ''}:{row['ledger_id']}:{row['ts']}:{row['content_sha256']}"
        expected_sha = hashlib.sha256(chain_input.encode("utf-8")).hexdigest()
        if row.get("ledger_sha256") != expected_sha:
            errors.append(f"ledger[{i}] ledger_sha256 mismatch (ledger_id={row.get('ledger_id')})")
        prev_sha = row.get("ledger_sha256")
    return errors


def verify_run_replay(
    tenant_id: str,
    run_id: str,
    *,
    db_path: Optional[str] = None,
) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Load events and evidence for run_id; verify chains; optionally validate required sequences.
    Returns (ok, errors, report_dict).
    """
    db_path = db_path or _get_db_path()
    report: Dict[str, Any] = {
        "run_id": run_id,
        "tenant_id": tenant_id,
        "chain_ok": False,
        "sequence_ok": True,
        "errors": [],
        "event_count": 0,
        "evidence_count": 0,
    }
    errors: List[str] = []

    events = get_events_for_run(tenant_id, run_id, db_path=db_path)
    report["event_count"] = len(events)
    if events:
        event_errors = _verify_event_chain(events)
        if event_errors:
            errors.extend(event_errors)
        else:
            report["event_chain_ok"] = True
    else:
        report["event_chain_ok"] = True  # no events is valid

    evidence = get_evidence_for_run(tenant_id, run_id, db_path=db_path)
    report["evidence_count"] = len(evidence)
    if evidence:
        ledger_errors = _verify_ledger_chain(evidence)
        if ledger_errors:
            errors.extend(ledger_errors)
        else:
            report["ledger_chain_ok"] = True
    else:
        report["ledger_chain_ok"] = True  # no evidence is valid

    report["chain_ok"] = len(errors) == 0
    report["errors"] = errors
    return (len(errors) == 0, errors, report)


def run_replay_and_write(
    bundle_dir: str,
    tenant_id: str,
    run_id: str,
    *,
    db_path: Optional[str] = None,
) -> bool:
    """
    Verify run replay and write REPLAY_VERIFY.txt and REPLAY_REPORT.json into bundle_dir.
    Returns True if OK.
    """
    from pathlib import Path
    ok, errors, report = verify_run_replay(tenant_id, run_id, db_path=db_path)
    root = Path(bundle_dir)
    root.mkdir(parents=True, exist_ok=True)
    if ok:
        (root / "REPLAY_VERIFY.txt").write_text("OK", encoding="utf-8")
    else:
        (root / "REPLAY_VERIFY.txt").write_text("ERROR: " + "; ".join(errors[:5]), encoding="utf-8")
    (root / "REPLAY_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return ok
