"""
Retention, redaction, and purge.

Artifact class buckets, retention enforcement, redaction filters (keys, tokens,
auth headers), purge by run_id/date/workflow with audit log and tombstones.
See hg_core/task_graph/docs/retention_redaction_purge_spec.md.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

AUDIT_DIR = "memory/automation/audit"
PURGE_AUDIT_FILE = "purge_audit.jsonl"

# Keys/patterns to redact (no secrets in stored artifacts)
REDACT_KEYS = {"api_key", "token", "Authorization", "Bearer", "password", "secret", "auth_header"}
REDACT_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_-]{20,}", re.I),
    re.compile(r"ghp_[a-zA-Z0-9]{36}", re.I),
    re.compile(r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", re.I),
]


def redact_for_storage(payload: Any) -> Any:
    """
    Redact known secrets from a payload for safe storage. Returns a copy with
    sensitive keys and pattern-matched values replaced by [REDACTED].
    """
    if isinstance(payload, dict):
        out = {}
        for k, v in payload.items():
            key_lower = k.lower() if isinstance(k, str) else ""
            if any(rk in key_lower for rk in ("key", "token", "auth", "password", "secret")):
                out[k] = "[REDACTED]"
            else:
                out[k] = redact_for_storage(v)
        return out
    if isinstance(payload, list):
        return [redact_for_storage(x) for x in payload]
    if isinstance(payload, str):
        for pat in REDACT_PATTERNS:
            if pat.search(payload):
                return "[REDACTED]"
    return payload


def purge_by_run_id(
    workspace_root: Path,
    run_id: str,
    run_base: str = "memory/automation/dag_runs",
) -> Tuple[List[Path], Optional[Dict[str, Any]]]:
    """
    Purge artifacts for a given run_id (e.g. run dir). Returns list of removed
    paths and an audit entry dict. Records the purge in the audit log.
    """
    root = Path(workspace_root)
    base = root / run_base
    removed: List[Path] = []
    for child in base.iterdir() if base.exists() else []:
        if child.is_dir() and run_id in child.name:
            for f in child.rglob("*"):
                if f.is_file():
                    try:
                        f.unlink()
                        removed.append(f)
                    except OSError as e:
                        logger.warning("Could not remove %s: %s", f, e)
            try:
                child.rmdir()
                removed.append(child)
            except OSError:
                pass
    audit_entry = {
        "action": "purge",
        "run_id": run_id,
        "removed_count": len(removed),
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    write_audit_log(root, audit_entry)
    return removed, audit_entry


def write_audit_log(workspace_root: Path, entry: Dict[str, Any]) -> None:
    """Append a purge (or other) audit entry to the audit log."""
    root = Path(workspace_root)
    audit_dir = root / AUDIT_DIR
    audit_dir.mkdir(parents=True, exist_ok=True)
    log_path = audit_dir / PURGE_AUDIT_FILE
    line = json.dumps(entry) + "\n"
    try:
        log_path.write_text(log_path.read_text() + line, encoding="utf-8")
    except FileNotFoundError:
        log_path.write_text(line, encoding="utf-8")


def purge_sensitive_leave_tombstone(artifact: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return a tombstone record: strip sensitive payloads, retain non-sensitive
    metrics and run_id. Add _tombstone=True.
    """
    tombstone = {"_tombstone": True, "run_id": artifact.get("run_id")}
    for k, v in artifact.items():
        if k in REDACT_KEYS or (isinstance(k, str) and "secret" in k.lower()):
            tombstone[k] = "[REDACTED]"
        elif k in ("metrics", "count", "status", "workflow_id"):
            tombstone[k] = v
        elif isinstance(v, (int, float, bool)) and k != "run_id":
            tombstone[k] = v
    return tombstone


# Artifact classes and retention buckets (for enforcement)
ARTIFACT_CLASSES = [
    "run_traces",
    "audit_summaries",
    "dead_letter",
    "approval_decisions",
    "output_artifacts",
    "knowledge_ingestion",
]
RETENTION_BUCKETS = {"short": "days_to_weeks", "medium": "weeks_to_months", "long": "months_plus"}
