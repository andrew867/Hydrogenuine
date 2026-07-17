from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional


def _workspace_root() -> Optional[Path]:
    try:
        from hg_lib.config import get_workspace_root

        return get_workspace_root()
    except Exception:
        return None


def _notifications_enabled() -> bool:
    raw = (os.environ.get("HG_APPROVAL_TELEGRAM_NOTIFICATIONS") or "").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    if raw in {"1", "true", "yes", "on"}:
        return True
    try:
        from hg_core.notification_telegram import is_telegram_configured

        return is_telegram_configured(_workspace_root())
    except Exception:
        return False


def _ledger_path(root: Path) -> Path:
    path = root / "memory" / "automation" / "notifications" / "approval_alerts.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _already_sent(path: Path, event_key: str) -> bool:
    try:
        if not path.exists():
            return False
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if str(payload.get("event_key") or "") == event_key:
                    return True
    except OSError:
        return False
    return False


def _append_ledger(path: Path, entry: dict[str, Any]) -> None:
    try:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _compact(text: str, limit: int) -> str:
    value = " ".join((text or "").split())
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 1)].rstrip() + "…"


def _escape_telegram_markdown(text: str) -> str:
    value = str(text or "")
    for needle in ("\\", "`", "*", "_", "[", "]"):
        value = value.replace(needle, f"\\{needle}")
    return value


def _notify_once(*, event_key: str, text: str, event_type: str, metadata: dict[str, Any]) -> dict[str, Any]:
    root = _workspace_root()
    if root is None:
        return {"ok": False, "error": "workspace_unavailable"}
    ledger = _ledger_path(root)
    if _already_sent(ledger, event_key):
        return {"ok": True, "deduped": True, "event_key": event_key}
    entry = {
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "event_key": event_key,
        "event_type": event_type,
        "text": text,
        "metadata": metadata,
        "delivery": {"attempted": False, "sent": False},
    }
    if _notifications_enabled():
        entry["delivery"]["attempted"] = True
        try:
            from hg_core.notification_telegram import send_telegram

            result = send_telegram(text, workspace_root=root)
        except Exception as exc:
            result = {"ok": False, "error": str(exc)}
        entry["delivery"]["result"] = result
        entry["delivery"]["sent"] = bool(result.get("ok"))
        if not result.get("ok") and result.get("error"):
            entry["delivery"]["error"] = result.get("error")
    else:
        entry["delivery"]["skipped"] = "disabled"
    _append_ledger(ledger, entry)
    return {"ok": bool(entry["delivery"].get("sent")), "event_key": event_key, "delivery": entry["delivery"]}


def notify_approval_created(
    *,
    approval_id: str,
    kind: str,
    title: str,
    summary: str,
    risk: str,
    requested_by: str,
    chat_id: Optional[str] = None,
    assigned_principal_id: Optional[str] = None,
) -> dict[str, Any]:
    safe_title = _escape_telegram_markdown(_compact(title, 120) or "Approval queued")
    safe_summary = _escape_telegram_markdown(_compact(summary, 160))
    safe_requested_by = _escape_telegram_markdown(requested_by or "")
    safe_assigned = _escape_telegram_markdown(assigned_principal_id or "")
    safe_chat_id = _escape_telegram_markdown(chat_id or "")
    lines = [
        "*Approval queued*",
        f"- title: {safe_title}",
        f"- kind: `{_escape_telegram_markdown((kind or 'unknown').strip() or 'unknown')}`",
        f"- risk: `{_escape_telegram_markdown((risk or 'unknown').strip() or 'unknown')}`",
    ]
    if safe_summary:
        lines.append(f"- summary: {safe_summary}")
    if safe_requested_by:
        lines.append(f"- requested_by: `{safe_requested_by}`")
    if safe_assigned:
        lines.append(f"- assigned_to: `{safe_assigned}`")
    if safe_chat_id:
        lines.append(f"- chat_id: `{safe_chat_id}`")
    lines.append(f"- approval_id: `{_escape_telegram_markdown(approval_id)}`")
    return _notify_once(
        event_key=f"approval-created:{approval_id}",
        text="\n".join(lines),
        event_type="approval_created",
        metadata={
            "approval_id": approval_id,
            "kind": kind,
            "risk": risk,
            "chat_id": chat_id,
            "assigned_principal_id": assigned_principal_id,
        },
    )


def notify_social_auto_approved(
    *,
    approval_id: str,
    task_name: str,
    platform: str,
    mode: str,
    title: str,
    content: str,
    thread_url: str,
    thread_id: Optional[str] = None,
) -> dict[str, Any]:
    safe_task_name = _escape_telegram_markdown((task_name or "unknown").strip() or "unknown")
    safe_platform = _escape_telegram_markdown((platform or "unknown").strip() or "unknown")
    safe_mode = _escape_telegram_markdown((mode or "unknown").strip() or "unknown")
    lines = [
        "*Social post auto-approved*",
        f"- workflow: `{safe_task_name}`",
        f"- platform: `{safe_platform}`",
        f"- mode: `{safe_mode}`",
    ]
    safe_title = _escape_telegram_markdown(_compact(title, 120))
    if safe_title:
        lines.append(f"- title: {safe_title}")
    snippet = _escape_telegram_markdown(_compact(content, 180))
    if snippet:
        lines.append(f"- excerpt: {snippet}")
    if thread_url:
        lines.append(f"- link: {_escape_telegram_markdown(thread_url)}")
    elif thread_id:
        lines.append(f"- thread_id: `{_escape_telegram_markdown(thread_id)}`")
    lines.append(f"- approval_id: `{_escape_telegram_markdown(approval_id)}`")
    return _notify_once(
        event_key=f"social-auto-approved:{approval_id}",
        text="\n".join(lines),
        event_type="social_auto_approved",
        metadata={
            "approval_id": approval_id,
            "task_name": task_name,
            "platform": platform,
            "mode": mode,
            "thread_url": thread_url,
            "thread_id": thread_id,
        },
    )
