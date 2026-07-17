from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from hg_gateway.db import get_connection
from hg_core.receipts import create_sealed_receipt


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def list_constitutional_roots() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM constitutional_roots ORDER BY updated_at DESC, workflow_family ASC").fetchall()
    return [dict(row) for row in rows]


def get_constitutional_root(root_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        root_row = conn.execute("SELECT * FROM constitutional_roots WHERE root_id = ?", (root_id,)).fetchone()
        if not root_row:
            return None
        checkpoints = conn.execute("SELECT * FROM constitutional_checkpoints WHERE root_id = ? ORDER BY created_at DESC LIMIT 20", (root_id,)).fetchall()
        drift_events = conn.execute("SELECT * FROM constitutional_drift_events WHERE root_id = ? ORDER BY created_at DESC LIMIT 20", (root_id,)).fetchall()
    return {"root": dict(root_row), "checkpoints": [dict(row) for row in checkpoints], "drift_events": [dict(row) for row in drift_events]}


def upsert_constitutional_root(
    *,
    root_id: str | None,
    workflow_family: str,
    title: str,
    root_goal: str,
    owner_id: str | None = None,
    accountable_actor: str | None = None,
    material_constraints: list[str] | None = None,
    approved_subgoals: list[str] | None = None,
    policy_version_id: str | None = None,
    status: str = "active",
    tenant_id: str = "default",
) -> dict[str, Any]:
    now = _iso_now()
    final_root_id = root_id or str(uuid.uuid4())
    with get_connection() as conn:
        existing = conn.execute("SELECT created_at FROM constitutional_roots WHERE root_id = ?", (final_root_id,)).fetchone()
        conn.execute(
            """
            INSERT OR REPLACE INTO constitutional_roots (
                root_id, workflow_family, title, root_goal, owner_id, accountable_actor,
                material_constraints_json, approved_subgoals_json, policy_version_id, status,
                drift_severity, last_checkpoint_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                final_root_id,
                workflow_family,
                title,
                root_goal,
                owner_id,
                accountable_actor,
                json.dumps(material_constraints or [], sort_keys=True),
                json.dumps(approved_subgoals or [], sort_keys=True),
                policy_version_id,
                status,
                "stable",
                None,
                str(existing["created_at"]) if existing else now,
                now,
            ),
        )
    create_sealed_receipt(
        tenant_id=tenant_id,
        receipt_kind="constitutional_root_upserted",
        subject_kind="constitutional_root",
        subject_id=final_root_id,
        policy_version_id=policy_version_id,
        constitutional_root_id=final_root_id,
        payload={
            "workflow_family": workflow_family,
            "title": title,
            "root_goal": root_goal,
            "material_constraints": material_constraints or [],
            "approved_subgoals": approved_subgoals or [],
            "status": status,
        },
    )
    return {"root_id": final_root_id, "updated_at": now}


def add_checkpoint(
    *,
    root_id: str,
    summary: str,
    state: dict[str, Any],
    alignment_score: float | None = None,
    actor_id: str | None = None,
    tenant_id: str = "default",
) -> dict[str, Any]:
    checkpoint_id = str(uuid.uuid4())
    created_at = _iso_now()
    receipt = create_sealed_receipt(
        tenant_id=tenant_id,
        receipt_kind="constitutional_checkpoint",
        subject_kind="constitutional_root",
        subject_id=root_id,
        actor_id=actor_id,
        constitutional_root_id=root_id,
        payload={"summary": summary, "state": state, "alignment_score": alignment_score},
    )
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO constitutional_checkpoints (checkpoint_id, root_id, summary, alignment_score, state_json, actor_id, created_at, receipt_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (checkpoint_id, root_id, summary, alignment_score, json.dumps(state, sort_keys=True), actor_id, created_at, receipt["receipt_id"]),
        )
        conn.execute("UPDATE constitutional_roots SET last_checkpoint_at = ?, updated_at = ? WHERE root_id = ?", (created_at, created_at, root_id))
    return {"checkpoint_id": checkpoint_id, "receipt_id": receipt["receipt_id"], "created_at": created_at}


def add_drift_event(
    *,
    root_id: str,
    severity: str,
    summary: str,
    details: dict[str, Any],
    actor_id: str | None = None,
    tenant_id: str = "default",
) -> dict[str, Any]:
    drift_event_id = str(uuid.uuid4())
    created_at = _iso_now()
    receipt = create_sealed_receipt(
        tenant_id=tenant_id,
        receipt_kind="constitutional_drift",
        subject_kind="constitutional_root",
        subject_id=root_id,
        actor_id=actor_id,
        constitutional_root_id=root_id,
        payload={"severity": severity, "summary": summary, "details": details},
    )
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO constitutional_drift_events (drift_event_id, root_id, severity, summary, details_json, acknowledged_at, acknowledged_by, override_status, created_at, receipt_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (drift_event_id, root_id, severity, summary, json.dumps(details, sort_keys=True), None, None, None, created_at, receipt["receipt_id"]),
        )
        conn.execute("UPDATE constitutional_roots SET drift_severity = ?, updated_at = ? WHERE root_id = ?", (severity, created_at, root_id))
    return {"drift_event_id": drift_event_id, "receipt_id": receipt["receipt_id"], "created_at": created_at}
