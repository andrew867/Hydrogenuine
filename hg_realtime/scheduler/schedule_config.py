"""Load and parse the realtime schedule. Prefer gateway DB, fall back to legacy JSON, and seed DB on first load."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from croniter import croniter
except ImportError:
    croniter = None  # type: ignore[assignment]


SCHEDULE_CONFIG_PATH = "memory/automation/realtime_schedule.json"
DEFAULT_TENANT_ID = "default"
DEFAULT_ACTOR_ID = "timer-source"
_HELD_SCHEDULE_DELAY_DAYS = 3650


@dataclass
class ScheduleEntry:
    """One scheduled job: job_id plus either cron expression or interval_minutes."""
    job_id: str
    cron: Optional[str] = None
    interval_minutes: Optional[float] = None
    inputs: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.cron is None and self.interval_minutes is None:
            raise ValueError("ScheduleEntry must have 'cron' or 'interval_minutes'")
        if self.cron is not None and self.interval_minutes is not None:
            raise ValueError("ScheduleEntry must have exactly one of 'cron' or 'interval_minutes'")


@dataclass
class ScheduleState:
    """Parsed schedule plus next run time per job_id."""
    entries: List[ScheduleEntry]
    next_run: Dict[str, datetime] = field(default_factory=dict)
    workspace_root: Optional[Path] = None

    def next_due(self, after: Optional[datetime] = None) -> Optional[tuple[datetime, ScheduleEntry]]:
        """Return (next_due_time, entry) for the soonest due job, or None if no entries."""
        ref = after or datetime.now(timezone.utc)
        soonest: Optional[tuple[datetime, ScheduleEntry]] = None
        for entry in self.entries:
            due = self.next_run.get(entry.job_id)
            if due is None:
                due = _compute_next(entry, ref, workspace_root=self.workspace_root)
                self.next_run[entry.job_id] = due
            if soonest is None or due < soonest[0]:
                soonest = (due, entry)
        return soonest

    def mark_fired(self, entry: ScheduleEntry, ref: datetime) -> None:
        """Advance next_run for this entry past ref (cron: next tick; interval: ref + interval)."""
        self.next_run[entry.job_id] = _compute_next(entry, ref, workspace_root=self.workspace_root)


def _compute_next(entry: ScheduleEntry, after: datetime, workspace_root: Optional[Path] = None) -> datetime:
    agency_mode = _agency_mode_for_entry(entry, workspace_root=workspace_root)
    if agency_mode == "held":
        return after + timedelta(days=_HELD_SCHEDULE_DELAY_DAYS)
    budget_reset_due = _agency_budget_reset_due_for_entry(entry, after, workspace_root=workspace_root)
    if budget_reset_due is not None:
        return budget_reset_due
    override_due = _cadence_override_due(entry, after, workspace_root=workspace_root)
    if override_due is not None:
        return override_due
    if entry.cron is not None:
        if croniter is None:
            raise RuntimeError("croniter is required for cron schedules; pip install croniter")
        it = croniter(entry.cron, after)
        return it.get_next(datetime)
    if entry.interval_minutes is not None:
        return after + timedelta(minutes=entry.interval_minutes)
    raise ValueError("Entry must have cron or interval_minutes")


def load_schedule(workspace_root: Optional[Path] = None) -> ScheduleState:
    """Load schedule from gateway DB first, falling back to realtime_schedule.json.

    If the gateway DB has no active scheduled jobs yet but the legacy JSON exists,
    seed the DB from that JSON so future reads become DB-backed.
    """
    root = _workspace_root(workspace_root)
    entries, has_gateway_rows = _load_gateway_schedule_entries(root)
    if has_gateway_rows:
        return ScheduleState(entries=entries, workspace_root=root)
    file_entries = _load_legacy_schedule_entries(root)
    if file_entries:
        _seed_gateway_schedule_entries(file_entries, root)
    return ScheduleState(entries=file_entries, workspace_root=root)


def _load_legacy_schedule_entries(workspace_root: Optional[Path]) -> List[ScheduleEntry]:
    root = _workspace_root(workspace_root)
    path = (root or Path.cwd()) / SCHEDULE_CONFIG_PATH
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    entries: List[ScheduleEntry] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict) and item.get("job_id"):
                job_id = str(item["job_id"])
                cron = item.get("cron")
                interval = item.get("interval_minutes")
                if cron is None and interval is None:
                    continue
                if cron is not None and interval is not None:
                    interval = None
                inputs = dict(item.get("inputs") or {})
                entries.append(ScheduleEntry(job_id=job_id, cron=cron, interval_minutes=interval, inputs=inputs))
    return entries


def _gateway_db_path(workspace_root: Optional[Path]) -> str | None:
    env_path = (os.environ.get("HG_GATEWAY_DB_PATH") or "").strip()
    if env_path:
        return env_path
    root = _workspace_root(workspace_root)
    if root is None:
        return None
    return str((root / "memory" / "gateway.sqlite3").resolve())


def _load_gateway_schedule_entries(workspace_root: Optional[Path]) -> tuple[List[ScheduleEntry], bool]:
    try:
        from hg_gateway.db import get_connection
    except Exception:
        return [], False
    db_path = _gateway_db_path(workspace_root)
    try:
        with get_connection(db_path) as conn:
            total_row = conn.execute("SELECT COUNT(*) FROM scheduled_jobs").fetchone()
            rows = conn.execute(
                """
                SELECT job_id, cron, interval_minutes, inputs_json
                FROM scheduled_jobs
                WHERE status = 'active'
                ORDER BY job_id
                """
            ).fetchall()
    except Exception:
        return [], False
    has_rows = bool(int(total_row[0] or 0) if total_row else 0)
    entries: List[ScheduleEntry] = []
    for row in rows:
        job_id = str(row["job_id"] if isinstance(row, dict) else row[0]).strip()
        if not job_id:
            continue
        cron = row["cron"] if isinstance(row, dict) else row[1]
        interval = row["interval_minutes"] if isinstance(row, dict) else row[2]
        inputs_raw = row["inputs_json"] if isinstance(row, dict) else row[3]
        try:
            inputs = json.loads(inputs_raw) if inputs_raw else {}
        except (TypeError, json.JSONDecodeError):
            inputs = {}
        if not isinstance(inputs, dict):
            inputs = {}
        if cron is None and interval is None:
            continue
        if cron is not None and interval is not None:
            interval = None
        entries.append(ScheduleEntry(job_id=job_id, cron=cron, interval_minutes=interval, inputs=dict(inputs)))
    return entries, has_rows


def _seed_gateway_schedule_entries(entries: List[ScheduleEntry], workspace_root: Optional[Path]) -> None:
    if not entries:
        return
    try:
        from hg_gateway.db import get_connection
    except Exception:
        return
    db_path = _gateway_db_path(workspace_root)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        with get_connection(db_path) as conn:
            for entry in entries:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO scheduled_jobs (
                        tenant_id, job_id, cron, interval_minutes, inputs_json, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
                    """,
                    (
                        DEFAULT_TENANT_ID,
                        entry.job_id,
                        entry.cron,
                        entry.interval_minutes,
                        json.dumps(entry.inputs or {}),
                        now,
                        now,
                    ),
                )
    except Exception:
        return


def cadence_override_path_for_entry(entry: ScheduleEntry, workspace_root: Optional[Path]) -> Optional[Path]:
    root = _workspace_root(workspace_root)
    if root is None:
        return None
    try:
        from hg_core.job_registry import get_operational_agent_id
    except Exception:
        return None
    task_name = str((entry.inputs or {}).get("task_name") or "").strip()
    if not task_name:
        return None
    agent_id = str(get_operational_agent_id(task_name) or "").strip()
    if not agent_id:
        return None
    return root / "memory" / "automation" / f"automation-{agent_id}" / "cadence_request.json"


def agency_control_path_for_entry(entry: ScheduleEntry, workspace_root: Optional[Path]) -> Optional[Path]:
    root = _workspace_root(workspace_root)
    if root is None:
        return None
    try:
        from hg_core.job_registry import get_operational_agent_id
    except Exception:
        return None
    task_name = str((entry.inputs or {}).get("task_name") or "").strip()
    if not task_name:
        return None
    agent_id = str(get_operational_agent_id(task_name) or "").strip()
    if not agent_id:
        return None
    return root / "memory" / "automation" / f"automation-{agent_id}" / "agency_control.json"


def _agency_mode_for_entry(entry: ScheduleEntry, workspace_root: Optional[Path]) -> str:
    path = agency_control_path_for_entry(entry, workspace_root)
    if path is None or not path.exists():
        return "normal"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "review_only"
    if not isinstance(payload, dict):
        return "review_only"
    mode = str(payload.get("mode") or "normal").strip().lower()
    return mode if mode in {"normal", "review_only", "held"} else "review_only"


def _agency_budget_reset_due_for_entry(entry: ScheduleEntry, after: datetime, workspace_root: Optional[Path]) -> Optional[datetime]:
    root = _workspace_root(workspace_root)
    if root is None:
        return None
    try:
        from operator_console.server.app.services.operational_agency_control import build_agency_control_summary
        from hg_core.job_registry import get_operational_agent_id, get_operational_session_target
    except Exception:
        return None
    task_name = str((entry.inputs or {}).get("task_name") or "").strip()
    if not task_name:
        return None
    summary = build_agency_control_summary(
        root=root,
        binding={
            "operational_agent_id": get_operational_agent_id(task_name),
            "operational_session_target": get_operational_session_target(task_name),
        },
        session_target=task_name,
    )
    if not bool(summary.get("outbound_budget_exhausted")):
        return None
    raw_reset = str(summary.get("outbound_budget_next_reset_at") or "").strip()
    if not raw_reset:
        return None
    try:
        due = datetime.fromisoformat(raw_reset.replace("Z", "+00:00"))
    except ValueError:
        return None
    if due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)
    return due if due > after else after


def clear_cadence_override_for_entry(entry: ScheduleEntry, workspace_root: Optional[Path]) -> None:
    path = cadence_override_path_for_entry(entry, workspace_root)
    if path is None or not path.exists():
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        return


def _cadence_override_due(entry: ScheduleEntry, after: datetime, workspace_root: Optional[Path]) -> Optional[datetime]:
    path = cadence_override_path_for_entry(entry, workspace_root)
    if path is None or not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    requested_job_id = str(payload.get("job_id") or payload.get("scheduler_job_id") or "").strip()
    if requested_job_id and requested_job_id != entry.job_id:
        return None
    raw_not_before = str(payload.get("not_before") or "").strip()
    if not raw_not_before:
        return None
    try:
        due = datetime.fromisoformat(raw_not_before.replace("Z", "+00:00"))
    except ValueError:
        return None
    if due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)
    if due <= after:
        return after
    return due


def _workspace_root(workspace_root: Optional[Path] = None) -> Optional[Path]:
    if workspace_root is not None:
        return workspace_root
    try:
        from hg_lib.config import get_workspace_root
        return get_workspace_root()
    except Exception:
        return None
