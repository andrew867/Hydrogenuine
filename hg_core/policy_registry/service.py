from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from hg_gateway.db import get_connection
from hg_core.receipts import create_sealed_receipt


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def list_policy_registry() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT r.policy_key, r.title, r.category, r.description, r.current_version_id, r.created_at, r.updated_at,
                   v.version_number, v.state, v.change_summary
            FROM policy_registry r
            LEFT JOIN policy_versions v ON v.version_id = r.current_version_id
            ORDER BY r.updated_at DESC, r.policy_key ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_policy_version(version_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM policy_versions WHERE version_id = ?", (version_id,)).fetchone()
    return dict(row) if row else None


def create_policy_version(
    *,
    policy_key: str,
    title: str,
    category: str,
    description: str | None,
    content: dict[str, Any],
    rationale: str | None,
    change_summary: str | None,
    actor_id: str | None = None,
    tenant_id: str = "default",
) -> dict[str, Any]:
    created_at = _iso_now()
    with get_connection() as conn:
        existing = conn.execute(
            """
            SELECT version_id, policy_key, version_number, receipt_id
            FROM policy_versions
            WHERE policy_key = ? AND state = 'draft' AND content_json = ? AND COALESCE(rationale, '') = ? AND COALESCE(change_summary, '') = ?
            ORDER BY version_number DESC LIMIT 1
            """,
            (policy_key, json.dumps(content, sort_keys=True), rationale or "", change_summary or ""),
        ).fetchone()
        if existing:
            return {
                "version_id": str(existing["version_id"]),
                "policy_key": str(existing["policy_key"]),
                "version_number": int(existing["version_number"]),
                "receipt_id": str(existing["receipt_id"]) if existing["receipt_id"] else None,
            }
        row = conn.execute(
            "SELECT MAX(version_number) AS max_version FROM policy_versions WHERE policy_key = ?",
            (policy_key,),
        ).fetchone()
        version_number = int((row["max_version"] if row and row["max_version"] is not None else 0) or 0) + 1
        version_id = str(uuid.uuid4())
        prior = conn.execute(
            "SELECT content_json, version_id FROM policy_versions WHERE policy_key = ? ORDER BY version_number DESC LIMIT 1",
            (policy_key,),
        ).fetchone()
        prior_content = json.loads(str(prior["content_json"])) if prior and prior["content_json"] else {}
        diff = {
            "from_version_id": str(prior["version_id"]) if prior else None,
            "changed_keys": sorted(set(prior_content.keys()) | set(content.keys())),
        }
        conn.execute(
            """
            INSERT OR REPLACE INTO policy_registry (policy_key, title, category, description, current_version_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, COALESCE((SELECT current_version_id FROM policy_registry WHERE policy_key = ?), NULL), COALESCE((SELECT created_at FROM policy_registry WHERE policy_key = ?), ?), ?)
            """,
            (policy_key, title, category, description, policy_key, policy_key, created_at, created_at),
        )
        conn.execute(
            """
            INSERT INTO policy_versions (
                version_id, policy_key, version_number, state, rationale, change_summary,
                content_json, diff_json, simulation_summary_json, effect_metrics_json,
                created_at, activated_at, superseded_at, receipt_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                version_id,
                policy_key,
                version_number,
                "draft",
                rationale,
                change_summary,
                json.dumps(content, sort_keys=True),
                json.dumps(diff, sort_keys=True),
                json.dumps({}),
                json.dumps({}),
                created_at,
                None,
                None,
                None,
            ),
        )
    receipt = create_sealed_receipt(
        tenant_id=tenant_id,
        receipt_kind="policy_version_created",
        subject_kind="policy_version",
        subject_id=version_id,
        actor_id=actor_id,
        policy_key=policy_key,
        policy_version_id=version_id,
        payload={
            "policy_key": policy_key,
            "version_number": version_number,
            "state": "draft",
            "content": content,
            "diff": diff,
        },
    )
    with get_connection() as conn:
        conn.execute("UPDATE policy_versions SET receipt_id = ? WHERE version_id = ?", (receipt["receipt_id"], version_id))
    return {"version_id": version_id, "policy_key": policy_key, "version_number": version_number, "receipt_id": receipt["receipt_id"]}


def run_policy_simulation(
    *,
    version_id: str,
    scenario_label: str,
    inputs: dict[str, Any],
    actor_id: str | None = None,
    tenant_id: str = "default",
) -> dict[str, Any]:
    version = get_policy_version(version_id)
    if not version:
        raise KeyError(version_id)
    encoded_inputs = json.dumps(inputs, sort_keys=True)
    with get_connection() as conn:
        existing = conn.execute(
            """
            SELECT simulation_id, result_json, receipt_id
            FROM policy_simulations
            WHERE policy_version_id = ? AND scenario_label = ? AND inputs_json = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (version_id, scenario_label, encoded_inputs),
        ).fetchone()
        if existing:
            return {
                "simulation_id": str(existing["simulation_id"]),
                "version_id": version_id,
                "result": json.loads(str(existing["result_json"])),
                "receipt_id": str(existing["receipt_id"]) if existing["receipt_id"] else None,
            }
    content = json.loads(str(version["content_json"]))
    required = set(content.get("required_flags") or [])
    present = {key for key, value in inputs.items() if value}
    missing = sorted(required - present)
    result = {
        "missing_required_flags": missing,
        "pass": not missing,
        "score": max(0.0, 1.0 - (len(missing) * 0.2)),
    }
    simulation_id = str(uuid.uuid4())
    created_at = _iso_now()
    receipt = create_sealed_receipt(
        tenant_id=tenant_id,
        receipt_kind="policy_simulation",
        subject_kind="policy_version",
        subject_id=version_id,
        actor_id=actor_id,
        policy_key=str(version["policy_key"]),
        policy_version_id=version_id,
        payload={"scenario_label": scenario_label, "inputs": inputs, "result": result},
    )
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO policy_simulations (simulation_id, policy_version_id, scenario_label, inputs_json, result_json, created_at, receipt_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (simulation_id, version_id, scenario_label, encoded_inputs, json.dumps(result, sort_keys=True), created_at, receipt["receipt_id"]),
        )
        conn.execute(
            "UPDATE policy_versions SET simulation_summary_json = ? WHERE version_id = ?",
            (json.dumps(result, sort_keys=True), version_id),
        )
    return {"simulation_id": simulation_id, "version_id": version_id, "result": result, "receipt_id": receipt["receipt_id"]}


def activate_policy_version(version_id: str, *, actor_id: str | None = None, tenant_id: str = "default") -> dict[str, Any]:
    version = get_policy_version(version_id)
    if not version:
        raise KeyError(version_id)
    policy_key = str(version["policy_key"])
    if str(version.get("state") or "") == "active":
        return {
            "version_id": version_id,
            "policy_key": policy_key,
            "receipt_id": str(version.get("receipt_id") or ""),
            "activated_at": str(version.get("activated_at") or ""),
        }
    activated_at = _iso_now()
    receipt = create_sealed_receipt(
        tenant_id=tenant_id,
        receipt_kind="policy_activation",
        subject_kind="policy_version",
        subject_id=version_id,
        actor_id=actor_id,
        policy_key=policy_key,
        policy_version_id=version_id,
        payload={"policy_key": policy_key, "version_id": version_id, "activated_at": activated_at},
    )
    with get_connection() as conn:
        conn.execute(
            "UPDATE policy_versions SET state = 'superseded', superseded_at = ? WHERE policy_key = ? AND state = 'active'",
            (activated_at, policy_key),
        )
        conn.execute(
            "UPDATE policy_versions SET state = 'active', activated_at = ?, receipt_id = ? WHERE version_id = ?",
            (activated_at, receipt["receipt_id"], version_id),
        )
        conn.execute(
            "UPDATE policy_registry SET current_version_id = ?, updated_at = ? WHERE policy_key = ?",
            (version_id, activated_at, policy_key),
        )
    return {"version_id": version_id, "policy_key": policy_key, "receipt_id": receipt["receipt_id"], "activated_at": activated_at}


def rollback_policy_version(policy_key: str, *, actor_id: str | None = None, tenant_id: str = "default") -> dict[str, Any]:
    with get_connection() as conn:
        target = conn.execute(
            """
            SELECT version_id
            FROM policy_versions
            WHERE policy_key = ? AND state IN ('superseded', 'active')
            ORDER BY version_number DESC
            LIMIT 1 OFFSET 1
            """,
            (policy_key,),
        ).fetchone()
    if not target:
        raise KeyError(policy_key)
    return activate_policy_version(str(target["version_id"]), actor_id=actor_id, tenant_id=tenant_id)


def add_policy_feedback(
    *,
    version_id: str,
    summary: str,
    sentiment: str | None = None,
    details: dict[str, Any] | None = None,
    author_id: str | None = None,
) -> dict[str, Any]:
    feedback_id = str(uuid.uuid4())
    created_at = _iso_now()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO policy_feedback (feedback_id, policy_version_id, author_id, sentiment, summary, details_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (feedback_id, version_id, author_id, sentiment, summary, json.dumps(details or {}, sort_keys=True), created_at),
        )
    return {"feedback_id": feedback_id, "version_id": version_id, "created_at": created_at}
