from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from hg_core.receipts import create_sealed_receipt
from hg_gateway.db import get_connection
from hg_gateway.routes_documents import _chat_workspace_summary


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _extract_nodes(run: dict[str, Any]) -> list[dict[str, Any]]:
    labels = run.get("segment_labels")
    if isinstance(labels, list) and labels:
        return [
            {
                "node_id": str(uuid.uuid4()),
                "label": str(label),
                "summary": f"Segment {index + 1}",
                "depth": 0,
                "source_document_id": run.get("document_id"),
                "payload": {"kind": "segment_label", "label": label},
            }
            for index, label in enumerate(labels)
        ]
    variants = run.get("query_variants")
    if isinstance(variants, list) and variants:
        return [
            {
                "node_id": str(uuid.uuid4()),
                "label": str(variant),
                "summary": f"Query direction {index + 1}",
                "depth": 0,
                "source_document_id": None,
                "payload": {"kind": "query_variant", "query_variant": variant},
            }
            for index, variant in enumerate(variants)
        ]
    return []


def sync_workspace(*, tenant_id: str, chat_id: str, actor_id: str | None = None) -> dict[str, Any]:
    workspace = _chat_workspace_summary(tenant_id, chat_id)
    runs = workspace.get("runs") or []
    synced = 0
    now = _iso_now()
    with get_connection() as conn:
        for run in runs:
            research_run_id = str(run.get("message_id") or uuid.uuid4())
            payload = {
                "chat_id": chat_id,
                "workspace_kind": run.get("kind"),
                "title": run.get("title"),
                "query": run.get("query"),
                "document_id": run.get("document_id"),
                "plan_template": run.get("plan_template"),
                "assistant_excerpt": run.get("assistant_excerpt"),
            }
            existing = conn.execute(
                "SELECT receipt_id FROM research_runs WHERE research_run_id = ?",
                (research_run_id,),
            ).fetchone()
            receipt_id = str(existing["receipt_id"]) if existing and existing["receipt_id"] else None
            if not receipt_id:
                receipt = create_sealed_receipt(
                    tenant_id=tenant_id,
                    receipt_kind="research_workspace_sync",
                    subject_kind="research_run",
                    subject_id=research_run_id,
                    actor_id=actor_id,
                    payload=payload,
                    chat_id=chat_id,
                )
                receipt_id = receipt["receipt_id"]
            conn.execute(
                """
                INSERT OR REPLACE INTO research_runs (
                    research_run_id, tenant_id, chat_id, workspace_kind, source_message_id,
                    title, query_text, document_id, plan_template, assistant_message_id,
                    assistant_excerpt, provenance_json, policy_version_id, constitutional_root_id,
                    receipt_id, synced_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM research_runs WHERE research_run_id = ?), ?), ?)
                """,
                (
                    research_run_id,
                    tenant_id,
                    chat_id,
                    str(run.get("kind") or "research_summary"),
                    run.get("message_id"),
                    str(run.get("title") or "Research run"),
                    run.get("query"),
                    run.get("document_id"),
                    run.get("plan_template"),
                    run.get("assistant_message_id"),
                    run.get("assistant_excerpt"),
                    json.dumps(run, sort_keys=True),
                    None,
                    None,
                    receipt_id,
                    now,
                    research_run_id,
                    now,
                    now,
                ),
            )
            conn.execute("DELETE FROM research_decomposition_nodes WHERE research_run_id = ?", (research_run_id,))
            for node in _extract_nodes(run):
                conn.execute(
                    """
                    INSERT INTO research_decomposition_nodes (
                        node_id, research_run_id, tenant_id, chat_id, label, summary, depth, source_document_id, payload_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        node["node_id"],
                        research_run_id,
                        tenant_id,
                        chat_id,
                        node["label"],
                        node["summary"],
                        node["depth"],
                        node["source_document_id"],
                        json.dumps(node["payload"], sort_keys=True),
                        now,
                    ),
                )
            synced += 1
    return {"chat_id": chat_id, "synced_runs": synced, "workspace": workspace}


def list_research_runs(*, tenant_id: str, limit: int = 20) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT research_run_id, tenant_id, chat_id, workspace_kind, source_message_id,
                   title, query_text, document_id, plan_template, assistant_message_id,
                   assistant_excerpt, provenance_json, policy_version_id, constitutional_root_id,
                   receipt_id, synced_at, created_at, updated_at
            FROM research_runs
            WHERE tenant_id = ?
            ORDER BY created_at DESC, research_run_id DESC
            LIMIT ?
            """,
            (tenant_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def get_research_run(*, tenant_id: str, research_run_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        run_row = conn.execute(
            """
            SELECT research_run_id, tenant_id, chat_id, workspace_kind, source_message_id,
                   title, query_text, document_id, plan_template, assistant_message_id,
                   assistant_excerpt, provenance_json, policy_version_id, constitutional_root_id,
                   receipt_id, synced_at, created_at, updated_at
            FROM research_runs
            WHERE tenant_id = ? AND research_run_id = ?
            """,
            (tenant_id, research_run_id),
        ).fetchone()
        if not run_row:
            return None
        node_rows = conn.execute(
            """
            SELECT node_id, research_run_id, tenant_id, chat_id, label, summary, depth, source_document_id, payload_json, created_at
            FROM research_decomposition_nodes
            WHERE research_run_id = ?
            ORDER BY depth ASC, created_at ASC
            """,
            (research_run_id,),
        ).fetchall()
    run = dict(run_row)
    run["nodes"] = [dict(row) for row in node_rows]
    return run
