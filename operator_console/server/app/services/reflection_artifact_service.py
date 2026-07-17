from __future__ import annotations

import json
import os
from typing import Any

from hg_gateway.events_ledger import emit_event
from hg_gateway.artifact_registry import get_artifact_registry_entry, list_artifact_inventory, upsert_reflection_artifact
from hg_gateway.db import get_connection


def list_reflection_artifacts() -> list[dict[str, Any]]:
    with get_connection() as conn:
        return list_artifact_inventory(conn, "reflection")


def get_reflection_artifact(artifact_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        return get_artifact_registry_entry(conn, artifact_id)


def _runtime_tenant_id() -> str:
    return (os.getenv("HG_OPERATOR_TENANT_ID") or os.getenv("HG_DEFAULT_TENANT_ID") or "default").strip() or "default"


def _parse_payload_json(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(artifact, dict):
        return {}
    raw = artifact.get("payload_json")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            loaded = json.loads(raw)
            if isinstance(loaded, dict):
                return loaded
        except Exception:
            return {}
    return {}


def _reflection_review_change_summary(action: str, note: str | None = None) -> str:
    action_label = action.replace("_", " ").strip()
    if note:
        return f"{action_label} reflection artifact: {note}"
    return f"{action_label} reflection artifact"


def _emit_reflection_review_event(
    *,
    artifact_id: str,
    title: str,
    action: str,
    verification_status: str,
    reviewed_by: str | None,
    promoted_at: str | None,
    change_summary: str,
    note: str | None,
) -> None:
    payload = {
        "artifact_id": artifact_id,
        "title": title,
        "action": action,
        "verification_status": verification_status,
        "reviewed_by": reviewed_by,
        "promoted_at": promoted_at,
        "detail": change_summary,
        "note": note,
    }
    emit_event(
        _runtime_tenant_id(),
        f"reflection.artifact.{action}",
        payload,
        actor_type="operator",
        actor_id=reviewed_by or "operator_console",
        document_id=artifact_id,
    )


def _review_reflection_artifact(
    *,
    artifact_id: str,
    action: str,
    actor_id: str | None = None,
    reviewed_by: str | None = None,
    note: str | None = None,
    promoted_at: str | None = None,
) -> dict[str, Any]:
    existing = get_reflection_artifact(artifact_id)
    if existing is None:
        raise KeyError(f"reflection artifact not found: {artifact_id}")
    payload = _parse_payload_json(existing)
    title = str(payload.get("title") or existing.get("title") or artifact_id).strip() or artifact_id
    summary = str(payload.get("summary") or existing.get("summary") or "").strip()
    findings_json = payload.get("findings_json")
    if findings_json is None:
        findings_json = {}
    source_event_ids = payload.get("source_event_ids") if isinstance(payload.get("source_event_ids"), list) else existing.get("source_event_ids") or []
    source_memory_ids = payload.get("source_memory_ids") if isinstance(payload.get("source_memory_ids"), list) else existing.get("source_memory_ids") or []
    source_links = payload.get("source_links") if isinstance(payload.get("source_links"), list) else existing.get("source_links") or []
    confidence = payload.get("confidence") if isinstance(payload.get("confidence"), (int, float)) else existing.get("confidence") or 0.0
    verification_status = action
    resolved_reviewed_by = reviewed_by or actor_id or str(payload.get("reviewed_by") or existing.get("reviewed_by") or "operator_console").strip() or "operator_console"
    resolved_promoted_at = promoted_at
    if action == "promoted" and not resolved_promoted_at:
        from datetime import datetime, timezone

        resolved_promoted_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    change_summary = _reflection_review_change_summary(action, note)
    updated = upsert_reflection_artifact_service(
        artifact_id=artifact_id,
        title=title,
        summary=summary,
        findings_json=findings_json,
        source_event_ids=[str(item).strip() for item in source_event_ids if str(item).strip()],
        source_memory_ids=[str(item).strip() for item in source_memory_ids if str(item).strip()],
        source_links=[dict(item) for item in source_links if isinstance(item, dict)],
        confidence=float(confidence or 0.0),
        verification_status=verification_status,
        reviewed_by=resolved_reviewed_by,
        promoted_at=resolved_promoted_at,
        actor_id=actor_id or resolved_reviewed_by,
        change_summary=change_summary,
    )
    _emit_reflection_review_event(
        artifact_id=artifact_id,
        title=title,
        action=action,
        verification_status=verification_status,
        reviewed_by=resolved_reviewed_by,
        promoted_at=resolved_promoted_at,
        change_summary=change_summary,
        note=note,
    )
    return updated


def upsert_reflection_artifact_service(
    *,
    artifact_id: str,
    title: str,
    summary: str,
    findings_json: Any,
    source_event_ids: list[str] | None = None,
    source_memory_ids: list[str] | None = None,
    source_links: list[dict[str, Any]] | None = None,
    confidence: float = 0.0,
    verification_status: str = "provisional",
    reviewed_by: str | None = None,
    promoted_at: str | None = None,
    actor_id: str | None = None,
    change_summary: str | None = None,
) -> dict[str, Any]:
    with get_connection() as conn:
        return upsert_reflection_artifact(
            conn,
            artifact_id=artifact_id,
            title=title,
            summary=summary,
            findings_json=findings_json,
            source_event_ids=source_event_ids or [],
            source_memory_ids=source_memory_ids or [],
            source_links=source_links or [],
            confidence=confidence,
            verification_status=verification_status,
            reviewed_by=reviewed_by,
            promoted_at=promoted_at,
            actor_id=actor_id,
            change_summary=change_summary,
        )


def promote_reflection_artifact_service(
    *,
    artifact_id: str,
    actor_id: str | None = None,
    reviewed_by: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    return _review_reflection_artifact(
        artifact_id=artifact_id,
        action="promoted",
        actor_id=actor_id,
        reviewed_by=reviewed_by,
        note=note,
    )


def discard_reflection_artifact_service(
    *,
    artifact_id: str,
    actor_id: str | None = None,
    reviewed_by: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    return _review_reflection_artifact(
        artifact_id=artifact_id,
        action="discarded",
        actor_id=actor_id,
        reviewed_by=reviewed_by,
        note=note,
    )


def escalate_reflection_artifact_service(
    *,
    artifact_id: str,
    actor_id: str | None = None,
    reviewed_by: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    return _review_reflection_artifact(
        artifact_id=artifact_id,
        action="escalated",
        actor_id=actor_id,
        reviewed_by=reviewed_by,
        note=note,
    )
