"""Ownership state store with CAS updates. Backed by SQLite (ownership_state table)."""
from __future__ import annotations
from typing import Any, Callable, List, Optional, Tuple

from .ownership_models import OwnershipRecord
from . import ownership_db


class OwnershipStore:
    """Current ownership state per (run_id, task_id). CAS updates via ownership_db."""

    def __init__(self, database_path: str, run_id: str):
        self.database_path = database_path
        self.run_id = run_id
        ownership_db.init_ownership_schema(self.database_path)

    def get_task(self, task_id: str) -> OwnershipRecord:
        row = ownership_db.state_get(self.database_path, self.run_id, task_id)
        if row is None:
            return OwnershipRecord(task_id=task_id)
        return OwnershipRecord(
            task_id=row.get("task_id", task_id),
            version=int(row.get("version", 0)),
            sponsor_id=row.get("sponsor_id") or "",
            accountable_id=row.get("accountable_id") or "",
            executor_id=row.get("executor_id") or "",
            current_token_id=row.get("current_token_id") or "",
            lease_expires_ts=float(row.get("lease_expires_ts") or 0),
            state=row.get("state") or "assigned",
            approver_spec=row.get("approver_spec"),
            escalation_spec=row.get("escalation_spec"),
            checkpoint_id=row.get("checkpoint_id"),
            last_event_ts=float(row.get("last_event_ts") or 0),
            contested_claims=row.get("contested_claims"),
        )

    def cas_update(
        self,
        task_id: str,
        expected_version: int,
        mutate_fn: Callable[[OwnershipRecord], None],
    ) -> Tuple[bool, Optional[OwnershipRecord], Optional[str]]:
        return ownership_db.state_cas_update(
            self.database_path,
            self.run_id,
            task_id,
            expected_version,
            mutate_fn,
        )

    def list_expired_leases(self, now_ts: Optional[float] = None) -> list:
        """Return list of state dicts for tasks with expired lease (acknowledged/in_progress)."""
        return ownership_db.state_list_expired_leases(
            self.database_path,
            self.run_id,
            now_ts=now_ts,
        )

    def get_chain(self, task_id: Optional[str] = None) -> list:
        """Return ownership chain snapshot(s) for this run (Phase 4 graph)."""
        return ownership_db.get_chain(self.database_path, self.run_id, task_id=task_id)

    def get_chain_edges(self, task_id: Optional[str] = None) -> list:
        """Return ownership chain edges for graph view (Phase 4)."""
        return ownership_db.get_chain_edges(self.database_path, self.run_id, task_id=task_id)

    def get_current_lead_and_scopes(self, task_id: str) -> Tuple[Optional[str], list]:
        """Chapter2: Return (current_lead_agent_id, list of contributor scope dicts). Lead = executor when state is acknowledged/in_progress."""
        rec = self.get_task(task_id)
        lead = None
        if rec.state in ("acknowledged", "in_progress", "pending_review") and rec.executor_id:
            lead = rec.executor_id
        scopes: list = []  # Phase 4: contributor scopes
        return (lead, scopes)
