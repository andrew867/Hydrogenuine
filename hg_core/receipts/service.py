from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from hg_gateway.db import get_connection
from hg_gateway.events_ledger import _append_evidence_conn, _emit_event_conn


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _current_seal_key_id() -> str:
    return (os.environ.get("HG_RECEIPT_SEAL_KEY_ID") or "workspace-default").strip() or "workspace-default"


def _receipt_chain_prev(conn: Any, tenant_id: str) -> str | None:
    row = conn.execute(
        "SELECT receipt_sha256 FROM sealed_receipts WHERE tenant_id = ? ORDER BY created_at DESC LIMIT 1",
        (tenant_id,),
    ).fetchone()
    return str(row[0]) if row else None


def create_sealed_receipt(
    *,
    tenant_id: str,
    receipt_kind: str,
    subject_kind: str,
    subject_id: str,
    payload: dict[str, Any],
    actor_type: str | None = "operator",
    actor_id: str | None = None,
    run_id: str | None = None,
    chat_id: str | None = None,
    turn_id: str | None = None,
    tool_call_id: str | None = None,
    approval_id: str | None = None,
    policy_key: str | None = None,
    policy_version_id: str | None = None,
    gate_family: str | None = None,
    constitutional_root_id: str | None = None,
    supersedes_receipt_id: str | None = None,
) -> dict[str, Any]:
    receipt_id = str(uuid.uuid4())
    created_at = _iso_now()
    canonical_json = _canonical_json(payload)
    canonical_sha256 = _sha256_text(canonical_json)
    seal_algorithm = "sha256-chain-v1"
    seal_key_id = _current_seal_key_id()
    with get_connection() as conn:
        prev_receipt_sha256 = _receipt_chain_prev(conn, tenant_id)
        receipt_sha256 = _sha256_text(
            ":".join(
                [
                    prev_receipt_sha256 or "",
                    receipt_id,
                    receipt_kind,
                    subject_kind,
                    subject_id,
                    canonical_sha256,
                    created_at,
                ]
            )
        )
        ledger_id = _append_evidence_conn(
            conn,
            tenant_id,
            "sealed_receipt",
            canonical_sha256,
            content_bytes=canonical_json.encode("utf-8"),
            run_id=run_id,
            chat_id=chat_id,
            turn_id=turn_id,
            tool_call_id=tool_call_id,
            approval_id=approval_id,
        )
        event_id = _emit_event_conn(
            conn,
            tenant_id,
            "receipt.sealed",
            {
                "receipt_id": receipt_id,
                "receipt_kind": receipt_kind,
                "subject_kind": subject_kind,
                "subject_id": subject_id,
                "canonical_sha256": canonical_sha256,
                "ledger_id": ledger_id,
            },
            actor_type=actor_type,
            actor_id=actor_id,
            run_id=run_id,
            chat_id=chat_id,
            turn_id=turn_id,
            tool_call_id=tool_call_id,
            approval_id=approval_id,
        )
        conn.execute(
            """
            INSERT INTO sealed_receipts (
                receipt_id, tenant_id, receipt_kind, subject_kind, subject_id,
                run_id, chat_id, turn_id, tool_call_id, approval_id, policy_key, policy_version_id,
                gate_family, constitutional_root_id, canonical_json, canonical_sha256,
                prev_receipt_sha256, receipt_sha256, seal_algorithm, seal_key_id,
                verification_status, event_id, ledger_id, supersedes_receipt_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                receipt_id,
                tenant_id,
                receipt_kind,
                subject_kind,
                subject_id,
                run_id,
                chat_id,
                turn_id,
                tool_call_id,
                approval_id,
                policy_key,
                policy_version_id,
                gate_family,
                constitutional_root_id,
                canonical_json,
                canonical_sha256,
                prev_receipt_sha256,
                receipt_sha256,
                seal_algorithm,
                seal_key_id,
                "verified",
                event_id,
                ledger_id,
                supersedes_receipt_id,
                created_at,
            ),
        )
    return {
        "receipt_id": receipt_id,
        "receipt_kind": receipt_kind,
        "subject_kind": subject_kind,
        "subject_id": subject_id,
        "canonical_sha256": canonical_sha256,
        "receipt_sha256": receipt_sha256,
        "verification_status": "verified",
        "event_id": event_id,
        "ledger_id": ledger_id,
        "created_at": created_at,
    }


def get_receipt(receipt_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM sealed_receipts WHERE receipt_id = ?", (receipt_id,)).fetchone()
    return dict(row) if row else None


def list_receipts(*, tenant_id: str | None = None, receipt_kind: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    sql = "SELECT * FROM sealed_receipts WHERE 1=1"
    params: list[Any] = []
    if tenant_id:
        sql += " AND tenant_id = ?"
        params.append(tenant_id)
    if receipt_kind:
        sql += " AND receipt_kind = ?"
        params.append(receipt_kind)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


def export_receipt(receipt_id: str) -> dict[str, Any]:
    receipt = get_receipt(receipt_id)
    if not receipt:
        raise KeyError(receipt_id)
    return {"receipt": receipt, "verification": verify_receipt(receipt_id, persist=False)}


def verify_receipt(receipt_id: str, *, persist: bool = True) -> dict[str, Any]:
    receipt = get_receipt(receipt_id)
    if not receipt:
        raise KeyError(receipt_id)
    canonical_sha256 = _sha256_text(str(receipt["canonical_json"]))
    receipt_sha256 = _sha256_text(
        ":".join(
            [
                str(receipt.get("prev_receipt_sha256") or ""),
                str(receipt["receipt_id"]),
                str(receipt["receipt_kind"]),
                str(receipt["subject_kind"]),
                str(receipt["subject_id"]),
                canonical_sha256,
                str(receipt["created_at"]),
            ]
        )
    )
    verification_status = "verified" if canonical_sha256 == receipt.get("canonical_sha256") and receipt_sha256 == receipt.get("receipt_sha256") else "failed"
    ledger_ok = True
    with get_connection() as conn:
        ledger_id = receipt.get("ledger_id")
        if ledger_id:
            ledger_row = conn.execute(
                "SELECT content_sha256 FROM evidence_ledger WHERE ledger_id = ?",
                (ledger_id,),
            ).fetchone()
            ledger_ok = bool(ledger_row and str(ledger_row["content_sha256"]) == canonical_sha256)
        if persist:
            conn.execute(
                "UPDATE sealed_receipts SET verification_status = ? WHERE receipt_id = ?",
                ("verified" if verification_status == "verified" and ledger_ok else "failed", receipt_id),
            )
    receipt["canonical_sha256"] = canonical_sha256
    receipt["receipt_sha256"] = receipt_sha256
    receipt["ledger_ok"] = ledger_ok
    receipt["verification_status"] = "verified" if verification_status == "verified" and ledger_ok else "failed"
    return receipt


def receipt_is_fresh(created_at: str, *, max_age_hours: float) -> bool:
    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    return created >= datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
