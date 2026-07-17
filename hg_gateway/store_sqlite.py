"""
SQLite-backed store for chats, messages, agents, approvals, and events.
Uses hg_gateway.db for connection and migrations.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from hg_gateway.db import get_connection, _get_db_path
from hg_gateway.models import LIFECYCLE_ACTIVE, AgentRow, ApprovalRow, ChatRow, MessageRow

_UNSET = object()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _is_broken_generated_title(title: Optional[str]) -> bool:
    value = re.sub(r"\s+", " ", str(title or "").strip()).lower()
    if not value:
        return True
    broken_prefixes = (
        "i don't have",
        "i don’t have",
        "i dont have",
        "i do not have",
        "i can’t",
        "i can't",
        "i cannot",
        "i'm unable",
        "im unable",
        "i am unable",
        "i don’t have access",
        "i don't have access",
        "i do not have access",
    )
    return value.startswith(broken_prefixes)


def _truncate_title_from_user_content(content: str) -> str:
    text = re.sub(r"\s+", " ", (content or "").strip())
    if not text:
        return "New chat"
    if len(text) <= 56:
        return text
    return text[:53].rstrip(" ,.;:-") + "..."


class SQLiteStore:
    """Durable store backed by SQLite. Pack3: all methods take tenant_id first; all queries scoped by tenant."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = db_path or _get_db_path()

    def _conn(self):
        return get_connection(self._db_path)

    def _auto_archive_stale_chats(self, conn: Any, tenant_id: str) -> None:
        raw_days = str(os.environ.get("HG_CHAT_AUTO_ARCHIVE_DAYS", "30")).strip()
        try:
            days = max(1, int(raw_days))
        except (TypeError, ValueError):
            days = 30
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        rows = conn.execute(
            """SELECT chat_id, updated_at
               FROM chats
               WHERE tenant_id = ? AND archived_at IS NULL""",
            (tenant_id,),
        ).fetchall()
        for row in rows:
            updated_at = _parse_iso(row["updated_at"])
            if updated_at is None or updated_at >= cutoff:
                continue
            conn.execute(
                """UPDATE chats
                   SET archived_at = ?, archive_reason = ?
                   WHERE tenant_id = ? AND chat_id = ?""",
                (_now(), "auto_stale", tenant_id, row["chat_id"]),
            )

    def _repair_chat_title(self, conn: Any, tenant_id: str, chat_id: str, title: Optional[str]) -> str:
        current = str(title or "").strip() or "New chat"
        if not _is_broken_generated_title(current):
            return current
        row = conn.execute(
            """SELECT content
               FROM messages
               WHERE tenant_id = ? AND chat_id = ? AND role = 'user'
               ORDER BY created_at ASC
               LIMIT 1""",
            (tenant_id, chat_id),
        ).fetchone()
        if not row or not str(row["content"] or "").strip():
            return current
        repaired = _truncate_title_from_user_content(str(row["content"]))
        if repaired and repaired != current:
            conn.execute(
                "UPDATE chats SET title = ? WHERE tenant_id = ? AND chat_id = ?",
                (repaired, tenant_id, chat_id),
            )
            return repaired
        return current

    def chat_list(
        self,
        tenant_id: str,
        include_archived: bool = False,
        archived_only: bool = False,
        include_deleted: bool = False,
        deleted_only: bool = False,
    ) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            self._auto_archive_stale_chats(conn, tenant_id)
            where = "tenant_id = ?"
            params: List[Any] = [tenant_id]
            if deleted_only:
                where += " AND deleted_at IS NOT NULL"
            elif not include_deleted:
                where += " AND deleted_at IS NULL"
            if archived_only:
                where += " AND archived_at IS NOT NULL"
            elif not include_archived:
                where += " AND archived_at IS NULL"
            rows = conn.execute(
                f"""SELECT chat_id, title, updated_at, unread_count, fingerprint_id, skin_id, swarm_run_id, swarm_role,
                           archived_at, archive_reason, deleted_at, delete_reason, restore_deadline_at
                    FROM chats WHERE {where} ORDER BY updated_at DESC""",
                tuple(params),
            ).fetchall()
            out = []
            for r in rows:
                title = self._repair_chat_title(conn, tenant_id, str(r["chat_id"]), r["title"])
                row = {
                    "chat_id": r["chat_id"],
                    "title": title,
                    "updated_at": r["updated_at"],
                    "unread_count": r["unread_count"],
                }
                if r["fingerprint_id"] is not None:
                    row["fingerprint_id"] = r["fingerprint_id"]
                if r["skin_id"] is not None:
                    row["skin_id"] = r["skin_id"]
                if r["swarm_run_id"] is not None:
                    row["swarm_run_id"] = r["swarm_run_id"]
                if r["swarm_role"] is not None:
                    row["swarm_role"] = r["swarm_role"]
                if r["archived_at"] is not None:
                    row["archived_at"] = r["archived_at"]
                if r["archive_reason"] is not None:
                    row["archive_reason"] = r["archive_reason"]
                if r["deleted_at"] is not None:
                    row["deleted_at"] = r["deleted_at"]
                if r["delete_reason"] is not None:
                    row["delete_reason"] = r["delete_reason"]
                if r["restore_deadline_at"] is not None:
                    row["restore_deadline_at"] = r["restore_deadline_at"]
                out.append(row)
            return out

    def chat_create(
        self,
        tenant_id: str,
        title: Optional[str] = None,
        fingerprint_id: Optional[str] = None,
        skin_id: Optional[str] = None,
        swarm_run_id: Optional[str] = None,
        swarm_role: Optional[str] = None,
    ) -> str:
        chat_id = str(uuid.uuid4())
        now = _now()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO chats (chat_id, tenant_id, title, updated_at, unread_count, fingerprint_id, skin_id, swarm_run_id, swarm_role) VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?)",
                (chat_id, tenant_id, title or "New chat", now, fingerprint_id or None, skin_id or None, swarm_run_id, swarm_role),
            )
        return chat_id

    def chat_get(self, tenant_id: str, chat_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            r = conn.execute(
                """SELECT chat_id, title, updated_at, fingerprint_id, skin_id, steering_profile_ids, swarm_run_id, swarm_role,
                          archived_at, archive_reason, deleted_at, delete_reason, restore_deadline_at,
                          temporary_fingerprint_id, temporary_skin_id, temporary_turns_remaining
                   FROM chats WHERE tenant_id = ? AND chat_id = ?""",
                (tenant_id, chat_id),
            ).fetchone()
            if not r:
                return None
            out = {"chat_id": r["chat_id"], "title": self._repair_chat_title(conn, tenant_id, chat_id, r["title"]), "updated_at": r["updated_at"]}
            if r["fingerprint_id"] is not None:
                out["fingerprint_id"] = r["fingerprint_id"]
            if r["skin_id"] is not None:
                out["skin_id"] = r["skin_id"]
            if "steering_profile_ids" in r.keys() and r["steering_profile_ids"] is not None:
                out["steering_profile_ids"] = r["steering_profile_ids"]
            if r["swarm_run_id"] is not None:
                out["swarm_run_id"] = r["swarm_run_id"]
            if r["swarm_role"] is not None:
                out["swarm_role"] = r["swarm_role"]
            if r["archived_at"] is not None:
                out["archived_at"] = r["archived_at"]
            if r["archive_reason"] is not None:
                out["archive_reason"] = r["archive_reason"]
            if r["deleted_at"] is not None:
                out["deleted_at"] = r["deleted_at"]
            if r["delete_reason"] is not None:
                out["delete_reason"] = r["delete_reason"]
            if r["restore_deadline_at"] is not None:
                out["restore_deadline_at"] = r["restore_deadline_at"]
            if r["temporary_fingerprint_id"] is not None:
                out["temporary_fingerprint_id"] = r["temporary_fingerprint_id"]
            if r["temporary_skin_id"] is not None:
                out["temporary_skin_id"] = r["temporary_skin_id"]
            if r["temporary_turns_remaining"] is not None:
                out["temporary_turns_remaining"] = r["temporary_turns_remaining"]
            return out

    def chat_update(self, tenant_id: str, chat_id: str, title: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                "UPDATE chats SET title = ?, updated_at = ? WHERE tenant_id = ? AND chat_id = ?",
                (title, _now(), tenant_id, chat_id),
            )
            return cur.rowcount > 0

    def chat_patch(
        self,
        tenant_id: str,
        chat_id: str,
        *,
        title: Any = _UNSET,
        fingerprint_id: Any = _UNSET,
        skin_id: Any = _UNSET,
        swarm_run_id: Any = _UNSET,
        swarm_role: Any = _UNSET,
        temporary_fingerprint_id: Any = _UNSET,
        temporary_skin_id: Any = _UNSET,
        temporary_turns_remaining: Any = _UNSET,
    ) -> bool:
        fields: List[str] = []
        params: List[Any] = []
        if title is not _UNSET:
            fields.append("title = ?")
            params.append(title)
        if fingerprint_id is not _UNSET:
            fields.append("fingerprint_id = ?")
            params.append(fingerprint_id)
        if skin_id is not _UNSET:
            fields.append("skin_id = ?")
            params.append(skin_id)
        if swarm_run_id is not _UNSET:
            fields.append("swarm_run_id = ?")
            params.append(swarm_run_id)
        if swarm_role is not _UNSET:
            fields.append("swarm_role = ?")
            params.append(swarm_role)
        if temporary_fingerprint_id is not _UNSET:
            fields.append("temporary_fingerprint_id = ?")
            params.append(temporary_fingerprint_id)
        if temporary_skin_id is not _UNSET:
            fields.append("temporary_skin_id = ?")
            params.append(temporary_skin_id)
        if temporary_turns_remaining is not _UNSET:
            fields.append("temporary_turns_remaining = ?")
            params.append(temporary_turns_remaining)
        if not fields:
            return False
        fields.append("updated_at = ?")
        params.append(_now())
        params.extend([tenant_id, chat_id])
        with self._conn() as conn:
            cur = conn.execute(
                f"UPDATE chats SET {', '.join(fields)} WHERE tenant_id = ? AND chat_id = ?",
                tuple(params),
            )
            return cur.rowcount > 0

    def chat_consume_temporary_persona_turn(self, tenant_id: str, chat_id: str) -> None:
        with self._conn() as conn:
            row = conn.execute(
                """SELECT temporary_turns_remaining
                   FROM chats WHERE tenant_id = ? AND chat_id = ?""",
                (tenant_id, chat_id),
            ).fetchone()
            if not row or row["temporary_turns_remaining"] is None:
                return
            turns = int(row["temporary_turns_remaining"])
            if turns <= 1:
                conn.execute(
                    """UPDATE chats
                       SET temporary_fingerprint_id = NULL,
                           temporary_skin_id = NULL,
                           temporary_turns_remaining = NULL,
                           updated_at = ?
                       WHERE tenant_id = ? AND chat_id = ?""",
                    (_now(), tenant_id, chat_id),
                )
                return
            conn.execute(
                """UPDATE chats
                   SET temporary_turns_remaining = ?, updated_at = ?
                   WHERE tenant_id = ? AND chat_id = ?""",
                (turns - 1, _now(), tenant_id, chat_id),
            )

    def chat_list_by_swarm(self, tenant_id: str, swarm_run_id: str) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            self._auto_archive_stale_chats(conn, tenant_id)
            rows = conn.execute(
                """SELECT chat_id, title, updated_at, unread_count, fingerprint_id, skin_id, swarm_run_id, swarm_role,
                          archived_at, archive_reason, deleted_at, delete_reason, restore_deadline_at
                   FROM chats WHERE tenant_id = ? AND swarm_run_id = ? ORDER BY updated_at DESC""",
                (tenant_id, swarm_run_id),
            ).fetchall()
            out = []
            for r in rows:
                title = self._repair_chat_title(conn, tenant_id, str(r["chat_id"]), r["title"])
                row = {
                    "chat_id": r["chat_id"],
                    "title": title,
                    "updated_at": r["updated_at"],
                    "unread_count": r["unread_count"],
                }
                if r["fingerprint_id"] is not None:
                    row["fingerprint_id"] = r["fingerprint_id"]
                if r["skin_id"] is not None:
                    row["skin_id"] = r["skin_id"]
                if r["swarm_run_id"] is not None:
                    row["swarm_run_id"] = r["swarm_run_id"]
                if r["swarm_role"] is not None:
                    row["swarm_role"] = r["swarm_role"]
                if r["archived_at"] is not None:
                    row["archived_at"] = r["archived_at"]
                if r["archive_reason"] is not None:
                    row["archive_reason"] = r["archive_reason"]
                if r["deleted_at"] is not None:
                    row["deleted_at"] = r["deleted_at"]
                if r["delete_reason"] is not None:
                    row["delete_reason"] = r["delete_reason"]
                if r["restore_deadline_at"] is not None:
                    row["restore_deadline_at"] = r["restore_deadline_at"]
                out.append(row)
            return out

    def chat_set_archived(self, tenant_id: str, chat_id: str, archived: bool, reason: Optional[str] = None) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                """UPDATE chats
                   SET archived_at = ?, archive_reason = ?, updated_at = ?
                   WHERE tenant_id = ? AND chat_id = ?""",
                (_now() if archived else None, reason if archived else None, _now(), tenant_id, chat_id),
            )
            return cur.rowcount > 0

    def chat_set_deleted(self, tenant_id: str, chat_id: str, deleted: bool, reason: Optional[str] = None) -> bool:
        restore_deadline = None
        if deleted:
            restore_deadline = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat().replace("+00:00", "Z")
        with self._conn() as conn:
            cur = conn.execute(
                """UPDATE chats
                   SET deleted_at = ?, delete_reason = ?, restore_deadline_at = ?, updated_at = ?
                   WHERE tenant_id = ? AND chat_id = ?""",
                (_now() if deleted else None, reason if deleted else None, restore_deadline if deleted else None, _now(), tenant_id, chat_id),
            )
            return cur.rowcount > 0

    def chat_set_swarm_archived(self, tenant_id: str, swarm_run_id: str, archived: bool, reason: Optional[str] = None) -> Dict[str, Any]:
        chats = self.chat_list_by_swarm(tenant_id, swarm_run_id)
        updated_chat_ids: List[str] = []
        for chat in chats:
            chat_id = str(chat.get("chat_id") or "")
            if chat_id and self.chat_set_archived(tenant_id, chat_id, archived=archived, reason=reason):
                updated_chat_ids.append(chat_id)
        return {"updated_chat_ids": updated_chat_ids, "updated_count": len(updated_chat_ids)}

    def chat_set_swarm_deleted(self, tenant_id: str, swarm_run_id: str, deleted: bool, reason: Optional[str] = None) -> Dict[str, Any]:
        chats = self.chat_list_by_swarm(tenant_id, swarm_run_id)
        updated_chat_ids: List[str] = []
        for chat in chats:
            chat_id = str(chat.get("chat_id") or "")
            if chat_id and self.chat_set_deleted(tenant_id, chat_id, deleted=deleted, reason=reason):
                updated_chat_ids.append(chat_id)
        return {"updated_chat_ids": updated_chat_ids, "updated_count": len(updated_chat_ids)}

    def chat_delete(self, tenant_id: str, chat_id: str) -> bool:
        with self._conn() as conn:
            conn.execute(
                """DELETE FROM persona_naturalness_issues
                   WHERE tenant_id = ? AND turn_id IN
                   (SELECT turn_id FROM persona_naturalness_turns WHERE tenant_id = ? AND chat_id = ?)""",
                (tenant_id, tenant_id, chat_id),
            )
            conn.execute("DELETE FROM persona_naturalness_turns WHERE tenant_id = ? AND chat_id = ?", (tenant_id, chat_id))
            conn.execute("DELETE FROM persona_autonomy_turns WHERE tenant_id = ? AND chat_id = ?", (tenant_id, chat_id))
            conn.execute(
                """DELETE FROM turn_provenance WHERE tenant_id = ? AND message_id IN
                   (SELECT message_id FROM messages WHERE tenant_id = ? AND chat_id = ?)""",
                (tenant_id, tenant_id, chat_id),
            )
            conn.execute("DELETE FROM messages WHERE tenant_id = ? AND chat_id = ?", (tenant_id, chat_id))
            conn.execute("DELETE FROM agents WHERE tenant_id = ? AND chat_id = ?", (tenant_id, chat_id))
            conn.execute("DELETE FROM events WHERE tenant_id = ? AND chat_id = ?", (tenant_id, chat_id))
            conn.execute("DELETE FROM approval_chat_lock WHERE tenant_id = ? AND chat_id = ?", (tenant_id, chat_id))
            conn.execute("DELETE FROM chat_traits WHERE tenant_id = ? AND chat_id = ?", (tenant_id, chat_id))
            conn.execute("DELETE FROM chat_persona_state WHERE tenant_id = ? AND chat_id = ?", (tenant_id, chat_id))
            conn.execute("DELETE FROM chat_persona_autonomy_state WHERE tenant_id = ? AND chat_id = ?", (tenant_id, chat_id))
            cur = conn.execute("DELETE FROM chats WHERE tenant_id = ? AND chat_id = ?", (tenant_id, chat_id))
            return cur.rowcount > 0

    def chat_delete_swarm(self, tenant_id: str, swarm_run_id: str) -> Dict[str, Any]:
        chats = self.chat_list_by_swarm(tenant_id, swarm_run_id)
        deleted_chat_ids: List[str] = []
        for chat in chats:
            chat_id = str(chat.get("chat_id") or "")
            if chat_id and self.chat_delete(tenant_id, chat_id):
                deleted_chat_ids.append(chat_id)
        return {"deleted_chat_ids": deleted_chat_ids, "deleted_count": len(deleted_chat_ids)}

    def chat_get_traits(self, tenant_id: str, chat_id: str) -> Dict[str, float]:
        with self._conn() as conn:
            r = conn.execute(
                "SELECT traits_json FROM chat_traits WHERE tenant_id = ? AND chat_id = ?",
                (tenant_id, chat_id),
            ).fetchone()
            if not r or not r["traits_json"]:
                return {}
            try:
                return json.loads(r["traits_json"])
            except (json.JSONDecodeError, TypeError):
                return {}

    def chat_set_traits(self, tenant_id: str, chat_id: str, traits: Dict[str, float]) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO chat_traits (tenant_id, chat_id, traits_json) VALUES (?, ?, ?)",
                (tenant_id, chat_id, json.dumps(traits)),
            )

    def chat_get_persona_state(self, tenant_id: str, chat_id: str) -> Dict[str, Any]:
        with self._conn() as conn:
            r = conn.execute(
                "SELECT state_json FROM chat_persona_state WHERE tenant_id = ? AND chat_id = ?",
                (tenant_id, chat_id),
            ).fetchone()
            if not r or not r["state_json"]:
                return {}
            try:
                return json.loads(r["state_json"])
            except (json.JSONDecodeError, TypeError):
                return {}

    def chat_set_persona_state(self, tenant_id: str, chat_id: str, state: Dict[str, Any]) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO chat_persona_state (tenant_id, chat_id, state_json, updated_at)
                   VALUES (?, ?, ?, ?)""",
                (tenant_id, chat_id, json.dumps(state or {}), _now()),
            )

    def chat_get_persona_autonomy_state(self, tenant_id: str, chat_id: str) -> Dict[str, Any]:
        with self._conn() as conn:
            r = conn.execute(
                "SELECT state_json FROM chat_persona_autonomy_state WHERE tenant_id = ? AND chat_id = ?",
                (tenant_id, chat_id),
            ).fetchone()
            if not r or not r["state_json"]:
                return {}
            try:
                return json.loads(r["state_json"])
            except (json.JSONDecodeError, TypeError):
                return {}

    def chat_set_persona_autonomy_state(self, tenant_id: str, chat_id: str, state: Dict[str, Any]) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO chat_persona_autonomy_state (tenant_id, chat_id, state_json, updated_at)
                   VALUES (?, ?, ?, ?)""",
                (tenant_id, chat_id, json.dumps(state or {}), _now()),
            )

    def message_list(self, tenant_id: str, chat_id: str) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT message_id, chat_id, role, created_at, content, agent_id, tool_name, tool_payload, tool_result, approvals_required
                   FROM messages WHERE tenant_id = ? AND chat_id = ? ORDER BY created_at""",
                (tenant_id, chat_id),
            ).fetchall()
            return [_message_row_to_dict(r) for r in rows]

    def message_add(
        self,
        tenant_id: str,
        chat_id: str,
        role: str,
        content: str,
        agent_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        tool_payload: Optional[Dict] = None,
        tool_result: Optional[Dict] = None,
        approvals_required: Optional[bool] = None,
    ) -> MessageRow:
        message_id = str(uuid.uuid4())
        now = _now()
        tool_payload_json = json.dumps(tool_payload) if tool_payload is not None else None
        tool_result_json = json.dumps(tool_result) if tool_result is not None else None
        appr = 1 if approvals_required else 0 if approvals_required is False else None
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO messages (message_id, tenant_id, chat_id, role, created_at, content, agent_id, tool_name, tool_payload, tool_result, approvals_required)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (message_id, tenant_id, chat_id, role, now, content, agent_id, tool_name, tool_payload_json, tool_result_json, appr),
            )
            conn.execute("UPDATE chats SET updated_at = ? WHERE tenant_id = ? AND chat_id = ?", (now, tenant_id, chat_id))
        return MessageRow(
            message_id=message_id,
            chat_id=chat_id,
            role=role,
            created_at=now,
            content=content,
            agent_id=agent_id,
            tool_name=tool_name,
            tool_payload=tool_payload,
            tool_result=tool_result,
            approvals_required=approvals_required,
        )

    def agent_list(self, tenant_id: str, chat_id: str) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT agent_id, label, status, parent_agent_id,
                          COALESCE(lifecycle_state, 'active') AS lifecycle_state,
                          state_reason, state_updated_at, state_updated_by
                   FROM agents WHERE tenant_id = ? AND chat_id = ?""",
                (tenant_id, chat_id),
            ).fetchall()
            # Convert Row to dict (sqlite3.Row has no .get(); dict(zip(r.keys(), r)) is safe)
            agents = [dict(zip(r.keys(), r)) for r in rows]
            result = []
            for a in agents:
                children = [x["agent_id"] for x in agents if x.get("parent_agent_id") == a["agent_id"]]
                result.append({**a, "children": children})
            return result

    def agent_get_lifecycle(
        self, tenant_id: str, chat_id: str, agent_id: str
    ) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            r = conn.execute(
                """SELECT lifecycle_state, state_reason, state_updated_at, state_updated_by
                   FROM agents WHERE tenant_id = ? AND chat_id = ? AND agent_id = ?""",
                (tenant_id, chat_id, agent_id),
            ).fetchone()
            if not r:
                return None
            return {
                "lifecycle_state": r["lifecycle_state"] or LIFECYCLE_ACTIVE,
                "state_reason": r["state_reason"],
                "state_updated_at": r["state_updated_at"],
                "state_updated_by": r["state_updated_by"],
            }

    def agent_set_lifecycle(
        self,
        tenant_id: str,
        chat_id: str,
        agent_id: str,
        lifecycle_state: str,
        reason: Optional[str] = None,
        updated_by: Optional[str] = None,
    ) -> bool:
        now = _now()
        with self._conn() as conn:
            cur = conn.execute(
                """UPDATE agents SET lifecycle_state = ?, state_reason = ?, state_updated_at = ?, state_updated_by = ?
                   WHERE tenant_id = ? AND chat_id = ? AND agent_id = ?""",
                (lifecycle_state, reason, now, updated_by, tenant_id, chat_id, agent_id),
            )
            return cur.rowcount > 0

    def agent_upsert(
        self,
        tenant_id: str,
        chat_id: str,
        agent_id: str,
        label: str,
        status: str,
        parent_agent_id: Optional[str] = None,
        state_reason: Optional[str] = None,
    ) -> None:
        from datetime import datetime, timezone
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z") if state_reason else None
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO agents (tenant_id, chat_id, agent_id, label, status, parent_agent_id, lifecycle_state, state_reason, state_updated_at, state_updated_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                   ON CONFLICT(chat_id, agent_id) DO UPDATE SET
                     label=excluded.label, status=excluded.status, parent_agent_id=excluded.parent_agent_id,
                     state_reason=COALESCE(excluded.state_reason, agents.state_reason),
                     state_updated_at=COALESCE(excluded.state_updated_at, agents.state_updated_at)
                   """,
                (tenant_id, chat_id, agent_id, label, status, parent_agent_id, LIFECYCLE_ACTIVE, state_reason, now_iso),
            )

    def approval_list(
        self,
        tenant_id: str,
        status_filter: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ):
        """status_filter: None or 'pending' = only pending; 'all' = all; 'approved' = approved; 'denied' = denied.
        When limit is set, returns dict with keys 'approvals' (list) and 'total' (int). Otherwise returns list."""
        with self._conn() as conn:
            if status_filter in ("all", "approved", "denied"):
                if status_filter == "all":
                    status_clause = ""
                    params: tuple = (tenant_id,)
                    count_params: tuple = (tenant_id,)
                else:
                    status_clause = " AND a.status = ?"
                    params = (tenant_id, status_filter)
                    count_params = (tenant_id, status_filter)
                q = f"""SELECT a.id, a.created_at, a.resolved_at, a.status, a.kind, a.title, a.summary, a.risk, a.requested_by, a.payload, a.resolution_note, a.assigned_principal_id, l.chat_id
                   FROM approvals a
                   LEFT JOIN approval_chat_lock l ON l.approval_id = a.id AND l.tenant_id = a.tenant_id
                   WHERE a.tenant_id = ?{status_clause}
                   ORDER BY a.created_at DESC"""
                if limit is not None:
                    total = conn.execute(
                        "SELECT COUNT(*) FROM approvals a WHERE a.tenant_id = ?" + status_clause,
                        count_params,
                    ).fetchone()[0]
                    q += " LIMIT ? OFFSET ?"
                    params = params + (limit, offset or 0)
                rows = conn.execute(q, params).fetchall()
            else:
                if limit is not None:
                    total = conn.execute(
                        "SELECT COUNT(*) FROM approvals a WHERE a.tenant_id = ? AND a.status = 'pending'",
                        (tenant_id,),
                    ).fetchone()[0]
                q = """SELECT a.id, a.created_at, a.resolved_at, a.status, a.kind, a.title, a.summary, a.risk, a.requested_by, a.payload, a.resolution_note, a.assigned_principal_id, l.chat_id
                   FROM approvals a
                   LEFT JOIN approval_chat_lock l ON l.approval_id = a.id AND l.tenant_id = a.tenant_id
                   WHERE a.tenant_id = ? AND a.status = 'pending'
                   ORDER BY a.created_at DESC"""
                if limit is not None:
                    q += " LIMIT ? OFFSET ?"
                    params = (tenant_id, limit, offset or 0)
                else:
                    params = (tenant_id,)
                rows = conn.execute(q, params).fetchall()
            items = [
                {
                    "id": r["id"],
                    "createdAt": r["created_at"],
                    "resolvedAt": r["resolved_at"],
                    "status": r["status"],
                    "kind": r["kind"],
                    "title": r["title"],
                    "summary": r["summary"],
                    "risk": r["risk"],
                    "requestedBy": r["requested_by"],
                    "payload": json.loads(r["payload"]) if r["payload"] else {},
                    "resolutionNote": r["resolution_note"],
                    "assignedPrincipalId": r["assigned_principal_id"] if r["assigned_principal_id"] else None,
                    "chat_id": r["chat_id"],
                }
                for r in rows
            ]
            if limit is not None:
                return {"approvals": items, "total": total}
            return items

    def approval_add(
        self,
        tenant_id: str,
        kind: str,
        title: str,
        summary: str,
        risk: str,
        requested_by: str,
        payload: Dict[str, Any],
        chat_id: Optional[str] = None,
        assigned_principal_id: Optional[str] = None,
    ) -> str:
        aid = str(uuid.uuid4())
        now = _now()
        payload_json = json.dumps(payload)
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO approvals (id, tenant_id, created_at, resolved_at, status, kind, title, summary, risk, requested_by, payload, resolution_note, assigned_principal_id)
                   VALUES (?, ?, ?, NULL, 'pending', ?, ?, ?, ?, ?, ?, NULL, ?)""",
                (aid, tenant_id, now, kind, title, summary, risk, requested_by, payload_json, assigned_principal_id),
            )
            if chat_id:
                conn.execute(
                    "INSERT OR REPLACE INTO approval_chat_lock (approval_id, tenant_id, chat_id) VALUES (?, ?, ?)",
                    (aid, tenant_id, chat_id),
                )
        return aid

    def approval_get(self, tenant_id: str, approval_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            r = conn.execute(
                """SELECT id, created_at, resolved_at, status, kind, title, summary, risk, payload, assigned_principal_id, resolution_note
                   FROM approvals WHERE tenant_id = ? AND id = ?""",
                (tenant_id, approval_id),
            ).fetchone()
            if not r:
                return None
            lock = conn.execute(
                "SELECT chat_id FROM approval_chat_lock WHERE approval_id = ? AND tenant_id = ?",
                (approval_id, tenant_id),
            ).fetchone()
            chat_id = lock["chat_id"] if lock else None
            return {
                "id": r["id"],
                "created_at": r["created_at"],
                "resolved_at": r["resolved_at"],
                "status": r["status"],
                "kind": r["kind"],
                "title": r["title"],
                "summary": r["summary"] or "",
                "risk": r["risk"] or "",
                "payload": json.loads(r["payload"]) if r["payload"] else {},
                "chat_id": chat_id,
                "assigned_principal_id": r["assigned_principal_id"] if r["assigned_principal_id"] else None,
                "resolution_note": r["resolution_note"],
            }

    def approval_resolve(self, tenant_id: str, approval_id: str, decision: str, note: Optional[str] = None) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                "UPDATE approvals SET resolved_at = ?, status = ?, resolution_note = ? WHERE tenant_id = ? AND id = ?",
                (_now(), decision, note, tenant_id, approval_id),
            )
            return cur.rowcount > 0

    def approval_list_for_chat(self, tenant_id: str, chat_id: str) -> List[Dict[str, Any]]:
        """All approvals (any status) linked to this chat. For bundle export."""
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT a.id, a.created_at, a.resolved_at, a.status, a.kind, a.title, a.summary, a.risk,
                          a.requested_by, a.payload, a.resolution_note
                   FROM approvals a
                   INNER JOIN approval_chat_lock l ON l.approval_id = a.id AND l.tenant_id = a.tenant_id
                   WHERE a.tenant_id = ? AND l.chat_id = ?
                   ORDER BY a.created_at""",
                (tenant_id, chat_id),
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "created_at": r["created_at"],
                    "resolved_at": r["resolved_at"],
                    "status": r["status"],
                    "kind": r["kind"],
                    "title": r["title"],
                    "summary": r["summary"] or "",
                    "risk": r["risk"] or "",
                    "requested_by": r["requested_by"],
                    "payload": json.loads(r["payload"]) if r["payload"] else {},
                    "resolution_note": r["resolution_note"],
                    "chat_id": chat_id,
                }
                for r in rows
            ]

    def persona_naturalness_add_turn(self, tenant_id: str, payload: Dict[str, Any]) -> None:
        row = dict(payload or {})
        turn_id = str(row.get("turn_id") or row.get("message_id") or uuid.uuid4())
        created_at = str(row.get("created_at") or _now())
        issues = list(row.pop("issues", []) or [])
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO persona_naturalness_turns (
                       turn_id, tenant_id, chat_id, message_id, fingerprint_id, skin_id, swarm_run_id, swarm_role,
                       input_type, emotional_register, stress_level, chosen_register, chosen_entry_point,
                       tic_count, sample_overlap_score, recent_overlap_score,
                       regeneration_attempted, regeneration_succeeded, created_at
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    turn_id,
                    tenant_id,
                    row.get("chat_id"),
                    row.get("message_id"),
                    row.get("fingerprint_id"),
                    row.get("skin_id"),
                    row.get("swarm_run_id"),
                    row.get("swarm_role"),
                    row.get("input_type") or "mundane",
                    row.get("emotional_register") or "calm",
                    row.get("stress_level") or "none",
                    row.get("chosen_register") or "neutral",
                    row.get("chosen_entry_point") or "direct",
                    int(row.get("tic_count") or 0),
                    float(row.get("sample_overlap_score") or 0.0),
                    float(row.get("recent_overlap_score") or 0.0),
                    1 if row.get("regeneration_attempted") else 0,
                    1 if row.get("regeneration_succeeded") else 0,
                    created_at,
                ),
            )
            conn.execute("DELETE FROM persona_naturalness_issues WHERE tenant_id = ? AND turn_id = ?", (tenant_id, turn_id))
            for issue in issues:
                if isinstance(issue, str):
                    issue_code = issue
                    issue_payload: Dict[str, Any] = {}
                else:
                    issue_code = str(issue.get("issue_code") or issue.get("code") or "")
                    issue_payload = dict(issue.get("payload") or {})
                if not issue_code:
                    continue
                conn.execute(
                    """INSERT INTO persona_naturalness_issues (turn_id, tenant_id, issue_code, payload_json, created_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (turn_id, tenant_id, issue_code, json.dumps(issue_payload), created_at),
                )

    def persona_naturalness_list(
        self,
        tenant_id: str,
        *,
        fingerprint_id: Optional[str] = None,
        skin_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        swarm_run_id: Optional[str] = None,
        hours: Optional[float] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        where = ["tenant_id = ?"]
        params: List[Any] = [tenant_id]
        if fingerprint_id:
            where.append("fingerprint_id = ?")
            params.append(fingerprint_id)
        if skin_id:
            where.append("skin_id = ?")
            params.append(skin_id)
        if chat_id:
            where.append("chat_id = ?")
            params.append(chat_id)
        if swarm_run_id:
            where.append("swarm_run_id = ?")
            params.append(swarm_run_id)
        if hours is not None:
            params.append((datetime.now(timezone.utc) - timedelta(hours=float(hours))).isoformat().replace("+00:00", "Z"))
            where.append("created_at >= ?")
        params.append(max(0, int(limit)))
        with self._conn() as conn:
            rows = conn.execute(
                f"""SELECT turn_id, tenant_id, chat_id, message_id, fingerprint_id, skin_id, swarm_run_id, swarm_role,
                           input_type, emotional_register, stress_level, chosen_register, chosen_entry_point,
                           tic_count, sample_overlap_score, recent_overlap_score,
                           regeneration_attempted, regeneration_succeeded, created_at
                    FROM persona_naturalness_turns
                    WHERE {' AND '.join(where)}
                    ORDER BY created_at DESC
                    LIMIT ?""",
                tuple(params),
            ).fetchall()
            turn_ids = [str(row["turn_id"]) for row in rows]
            issues_by_turn: Dict[str, List[Dict[str, Any]]] = {}
            if turn_ids:
                placeholders = ", ".join("?" for _ in turn_ids)
                issue_rows = conn.execute(
                    f"""SELECT turn_id, issue_code, payload_json, created_at
                        FROM persona_naturalness_issues
                        WHERE tenant_id = ? AND turn_id IN ({placeholders})
                        ORDER BY id ASC""",
                    (tenant_id, *turn_ids),
                ).fetchall()
                for issue in issue_rows:
                    try:
                        payload = json.loads(issue["payload_json"]) if issue["payload_json"] else {}
                    except (json.JSONDecodeError, TypeError):
                        payload = {}
                    issues_by_turn.setdefault(str(issue["turn_id"]), []).append(
                        {
                            "issue_code": issue["issue_code"],
                            "payload": payload,
                            "created_at": issue["created_at"],
                        }
                    )
            out = []
            for row in rows:
                item = dict(row)
                item["regeneration_attempted"] = bool(item.get("regeneration_attempted"))
                item["regeneration_succeeded"] = bool(item.get("regeneration_succeeded"))
                item["issues"] = issues_by_turn.get(str(item.get("turn_id") or ""), [])
                out.append(item)
            return out

    def persona_naturalness_summary(
        self,
        tenant_id: str,
        *,
        fingerprint_id: Optional[str] = None,
        skin_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        swarm_run_id: Optional[str] = None,
        hours: Optional[float] = None,
    ) -> Dict[str, Any]:
        rows = self.persona_naturalness_list(
            tenant_id,
            fingerprint_id=fingerprint_id,
            skin_id=skin_id,
            chat_id=chat_id,
            swarm_run_id=swarm_run_id,
            hours=hours,
            limit=10000,
        )
        if not rows:
            return {
                "total_turns": 0,
                "unique_personas": 0,
                "average_sample_overlap": 0.0,
                "average_recent_overlap": 0.0,
                "regeneration_rate": 0.0,
                "regeneration_rescue_rate": 0.0,
                "stress_distribution": {},
                "register_distribution": {},
                "entry_point_distribution": {},
                "tic_frequency": 0.0,
                "top_issue_buckets": {},
            }
        total_turns = len(rows)
        regen_attempted = sum(1 for row in rows if row.get("regeneration_attempted"))
        regen_succeeded = sum(1 for row in rows if row.get("regeneration_succeeded"))
        stress_distribution: Dict[str, int] = {}
        register_distribution: Dict[str, int] = {}
        entry_point_distribution: Dict[str, int] = {}
        issue_buckets: Dict[str, int] = {}
        unique_personas = {
            (str(row.get("fingerprint_id") or ""), str(row.get("skin_id") or ""))
            for row in rows
            if row.get("fingerprint_id")
        }
        for row in rows:
            stress_key = str(row.get("stress_level") or "unknown")
            register_key = str(row.get("chosen_register") or "unknown")
            entry_point_key = str(row.get("chosen_entry_point") or "unknown")
            stress_distribution[stress_key] = stress_distribution.get(stress_key, 0) + 1
            register_distribution[register_key] = register_distribution.get(register_key, 0) + 1
            entry_point_distribution[entry_point_key] = entry_point_distribution.get(entry_point_key, 0) + 1
            for issue in row.get("issues", []) or []:
                code = str(issue.get("issue_code") or "unknown")
                issue_buckets[code] = issue_buckets.get(code, 0) + 1
        return {
            "total_turns": total_turns,
            "unique_personas": len(unique_personas),
            "average_sample_overlap": sum(float(row.get("sample_overlap_score") or 0.0) for row in rows) / total_turns,
            "average_recent_overlap": sum(float(row.get("recent_overlap_score") or 0.0) for row in rows) / total_turns,
            "regeneration_rate": regen_attempted / total_turns,
            "regeneration_rescue_rate": (regen_succeeded / regen_attempted) if regen_attempted else 0.0,
            "stress_distribution": stress_distribution,
            "register_distribution": register_distribution,
            "entry_point_distribution": entry_point_distribution,
            "tic_frequency": sum(int(row.get("tic_count") or 0) for row in rows) / total_turns,
            "top_issue_buckets": issue_buckets,
        }

    def persona_naturalness_swarm_summary(
        self,
        tenant_id: str,
        swarm_run_id: str,
        *,
        hours: Optional[float] = None,
    ) -> Dict[str, Any]:
        rows = self.persona_naturalness_list(tenant_id, swarm_run_id=swarm_run_id, hours=hours, limit=10000)
        member_breakdown: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            member_key = str(row.get("chat_id") or row.get("turn_id"))
            bucket = member_breakdown.setdefault(
                member_key,
                {
                    "chat_id": row.get("chat_id"),
                    "swarm_role": row.get("swarm_role"),
                    "fingerprint_id": row.get("fingerprint_id"),
                    "skin_id": row.get("skin_id"),
                    "turn_count": 0,
                    "average_sample_overlap": 0.0,
                    "average_recent_overlap": 0.0,
                    "regeneration_attempts": 0,
                    "regeneration_successes": 0,
                    "entry_points": {},
                },
            )
            bucket["turn_count"] += 1
            bucket["average_sample_overlap"] += float(row.get("sample_overlap_score") or 0.0)
            bucket["average_recent_overlap"] += float(row.get("recent_overlap_score") or 0.0)
            bucket["regeneration_attempts"] += 1 if row.get("regeneration_attempted") else 0
            bucket["regeneration_successes"] += 1 if row.get("regeneration_succeeded") else 0
            entry_point_key = str(row.get("chosen_entry_point") or "unknown")
            bucket["entry_points"][entry_point_key] = bucket["entry_points"].get(entry_point_key, 0) + 1
        members: List[Dict[str, Any]] = []
        orchestrator = None
        for bucket in member_breakdown.values():
            turn_count = int(bucket.get("turn_count") or 0)
            if turn_count:
                bucket["average_sample_overlap"] /= turn_count
                bucket["average_recent_overlap"] /= turn_count
            if bucket.get("swarm_role") == "orchestrator":
                orchestrator = dict(bucket)
            else:
                members.append(dict(bucket))
        return {
            "swarm_run_id": swarm_run_id,
            "summary": self.persona_naturalness_summary(tenant_id, swarm_run_id=swarm_run_id, hours=hours),
            "orchestrator": orchestrator,
            "members": members,
        }

    def persona_autonomy_add_turn(self, tenant_id: str, payload: Dict[str, Any]) -> None:
        row = dict(payload or {})
        turn_id = str(row.get("turn_id") or row.get("message_id") or uuid.uuid4())
        created_at = str(row.get("created_at") or _now())
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO persona_autonomy_turns (
                       turn_id, tenant_id, chat_id, message_id, fingerprint_id, skin_id, swarm_run_id, swarm_role,
                       arc_state, engagement_mode, depth_level, uncertainty_level,
                       callback_surface, proactive_notice, lateral_mode, position_evolution,
                       relationship_type, counterpart_fingerprint_id, details_json, created_at
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    turn_id,
                    tenant_id,
                    row.get("chat_id"),
                    row.get("message_id"),
                    row.get("fingerprint_id"),
                    row.get("skin_id"),
                    row.get("swarm_run_id"),
                    row.get("swarm_role"),
                    row.get("arc_state") or "unknown",
                    row.get("engagement_mode") or "direct",
                    row.get("depth_level") or "surface",
                    row.get("uncertainty_level") or "confident",
                    1 if row.get("callback_surface") else 0,
                    1 if row.get("proactive_notice") else 0,
                    row.get("lateral_mode") or "skip",
                    1 if row.get("position_evolution") else 0,
                    row.get("relationship_type"),
                    row.get("counterpart_fingerprint_id"),
                    json.dumps(row.get("details") or {}),
                    created_at,
                ),
            )

    def persona_autonomy_list(
        self,
        tenant_id: str,
        *,
        fingerprint_id: Optional[str] = None,
        skin_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        swarm_run_id: Optional[str] = None,
        hours: Optional[float] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        where = ["tenant_id = ?"]
        params: List[Any] = [tenant_id]
        if fingerprint_id:
            where.append("fingerprint_id = ?")
            params.append(fingerprint_id)
        if skin_id:
            where.append("skin_id = ?")
            params.append(skin_id)
        if chat_id:
            where.append("chat_id = ?")
            params.append(chat_id)
        if swarm_run_id:
            where.append("swarm_run_id = ?")
            params.append(swarm_run_id)
        if hours is not None:
            params.append((datetime.now(timezone.utc) - timedelta(hours=float(hours))).isoformat().replace("+00:00", "Z"))
            where.append("created_at >= ?")
        params.append(max(0, int(limit)))
        with self._conn() as conn:
            rows = conn.execute(
                f"""SELECT turn_id, tenant_id, chat_id, message_id, fingerprint_id, skin_id, swarm_run_id, swarm_role,
                           arc_state, engagement_mode, depth_level, uncertainty_level,
                           callback_surface, proactive_notice, lateral_mode, position_evolution,
                           relationship_type, counterpart_fingerprint_id, details_json, created_at
                    FROM persona_autonomy_turns
                    WHERE {' AND '.join(where)}
                    ORDER BY created_at DESC
                    LIMIT ?""",
                tuple(params),
            ).fetchall()
            out = []
            for row in rows:
                item = dict(row)
                item["callback_surface"] = bool(item.get("callback_surface"))
                item["proactive_notice"] = bool(item.get("proactive_notice"))
                item["position_evolution"] = bool(item.get("position_evolution"))
                try:
                    item["details"] = json.loads(item.get("details_json") or "{}")
                except (json.JSONDecodeError, TypeError):
                    item["details"] = {}
                item.pop("details_json", None)
                out.append(item)
            return out

    def persona_autonomy_summary(
        self,
        tenant_id: str,
        *,
        fingerprint_id: Optional[str] = None,
        skin_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        swarm_run_id: Optional[str] = None,
        hours: Optional[float] = None,
    ) -> Dict[str, Any]:
        rows = self.persona_autonomy_list(
            tenant_id,
            fingerprint_id=fingerprint_id,
            skin_id=skin_id,
            chat_id=chat_id,
            swarm_run_id=swarm_run_id,
            hours=hours,
            limit=10000,
        )
        if not rows:
            return {
                "total_turns": 0,
                "arc_distribution": {},
                "engagement_distribution": {},
                "uncertainty_distribution": {},
                "relationship_distribution": {},
                "callback_rate": 0.0,
                "proactive_notice_rate": 0.0,
                "position_evolution_rate": 0.0,
            }
        total_turns = len(rows)
        arc_distribution: Dict[str, int] = {}
        engagement_distribution: Dict[str, int] = {}
        uncertainty_distribution: Dict[str, int] = {}
        relationship_distribution: Dict[str, int] = {}
        callback_count = 0
        proactive_count = 0
        evolution_count = 0
        for row in rows:
            arc_distribution[str(row.get("arc_state") or "unknown")] = arc_distribution.get(str(row.get("arc_state") or "unknown"), 0) + 1
            engagement_distribution[str(row.get("engagement_mode") or "direct")] = engagement_distribution.get(str(row.get("engagement_mode") or "direct"), 0) + 1
            uncertainty_distribution[str(row.get("uncertainty_level") or "confident")] = uncertainty_distribution.get(str(row.get("uncertainty_level") or "confident"), 0) + 1
            relationship_distribution[str(row.get("relationship_type") or "none")] = relationship_distribution.get(str(row.get("relationship_type") or "none"), 0) + 1
            callback_count += 1 if row.get("callback_surface") else 0
            proactive_count += 1 if row.get("proactive_notice") else 0
            evolution_count += 1 if row.get("position_evolution") else 0
        return {
            "total_turns": total_turns,
            "arc_distribution": arc_distribution,
            "engagement_distribution": engagement_distribution,
            "uncertainty_distribution": uncertainty_distribution,
            "relationship_distribution": relationship_distribution,
            "callback_rate": callback_count / total_turns,
            "proactive_notice_rate": proactive_count / total_turns,
            "position_evolution_rate": evolution_count / total_turns,
        }

    def persona_autonomy_swarm_summary(
        self,
        tenant_id: str,
        swarm_run_id: str,
        *,
        hours: Optional[float] = None,
    ) -> Dict[str, Any]:
        rows = self.persona_autonomy_list(tenant_id, swarm_run_id=swarm_run_id, hours=hours, limit=10000)
        member_breakdown: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            member_key = str(row.get("chat_id") or row.get("turn_id"))
            bucket = member_breakdown.setdefault(
                member_key,
                {
                    "chat_id": row.get("chat_id"),
                    "swarm_role": row.get("swarm_role"),
                    "fingerprint_id": row.get("fingerprint_id"),
                    "turn_count": 0,
                    "relationship_types": {},
                    "engagement_modes": {},
                },
            )
            bucket["turn_count"] += 1
            relationship_key = str(row.get("relationship_type") or "none")
            engagement_key = str(row.get("engagement_mode") or "direct")
            bucket["relationship_types"][relationship_key] = bucket["relationship_types"].get(relationship_key, 0) + 1
            bucket["engagement_modes"][engagement_key] = bucket["engagement_modes"].get(engagement_key, 0) + 1
        members: List[Dict[str, Any]] = []
        orchestrator = None
        for bucket in member_breakdown.values():
            if bucket.get("swarm_role") == "orchestrator":
                orchestrator = dict(bucket)
            else:
                members.append(dict(bucket))
        return {
            "swarm_run_id": swarm_run_id,
            "summary": self.persona_autonomy_summary(tenant_id, swarm_run_id=swarm_run_id, hours=hours),
            "orchestrator": orchestrator,
            "members": members,
        }

    def event_append(self, tenant_id: str, chat_id: str, event_type: str, payload: Dict[str, Any]) -> None:
        """Append an event for SSE replay (optional)."""
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO events (tenant_id, chat_id, event_type, payload, created_at) VALUES (?, ?, ?, ?, ?)",
                (tenant_id, chat_id, event_type, json.dumps(payload), _now()),
            )

    def event_list(self, tenant_id: str, chat_id: str, since_created_at: Optional[str] = None) -> List[Dict[str, Any]]:
        """List events for a chat, optionally after a timestamp (for replay)."""
        with self._conn() as conn:
            if since_created_at:
                rows = conn.execute(
                    "SELECT event_type, payload, created_at FROM events WHERE tenant_id = ? AND chat_id = ? AND created_at > ? ORDER BY created_at",
                    (tenant_id, chat_id, since_created_at),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT event_type, payload, created_at FROM events WHERE tenant_id = ? AND chat_id = ? ORDER BY created_at",
                    (tenant_id, chat_id),
                ).fetchall()
            return [
                {"event_type": r["event_type"], "payload": json.loads(r["payload"]), "created_at": r["created_at"]}
                for r in rows
            ]

    def chat_tenant_id(self, chat_id: str) -> Optional[str]:
        """Return tenant_id that owns this chat_id, or None if not found. Used for cross-tenant detection."""
        with self._conn() as conn:
            r = conn.execute("SELECT tenant_id FROM chats WHERE chat_id = ?", (chat_id,)).fetchone()
            return r["tenant_id"] if r else None

    def audit_append(self, tenant_id: str, event_type: str, payload: Dict[str, Any]) -> None:
        """Record audit event (e.g. cross_tenant_access)."""
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO audit_events (tenant_id, event_type, payload, created_at) VALUES (?, ?, ?, ?)",
                (tenant_id, event_type, json.dumps(payload), _now()),
            )

    def audit_list(
        self,
        tenant_id: Optional[str] = None,
        *,
        event_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List audit events newest-first. When tenant_id is None, returns all tenants (admin)."""
        limit = max(1, min(int(limit), 500))
        offset = max(0, int(offset))
        clauses: List[str] = []
        params: List[Any] = []
        if tenant_id:
            clauses.append("tenant_id = ?")
            params.append(tenant_id)
        if event_type:
            clauses.append("event_type = ?")
            params.append(event_type)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._conn() as conn:
            total_row = conn.execute(
                f"SELECT COUNT(*) AS c FROM audit_events {where}",
                tuple(params),
            ).fetchone()
            total = int(total_row["c"]) if total_row else 0
            rows = conn.execute(
                f"""SELECT event_id, tenant_id, event_type, payload, created_at
                    FROM audit_events {where}
                    ORDER BY event_id DESC
                    LIMIT ? OFFSET ?""",
                tuple(params + [limit, offset]),
            ).fetchall()
        items = []
        for row in rows:
            try:
                payload = json.loads(row["payload"] or "{}")
            except json.JSONDecodeError:
                payload = {"raw": row["payload"]}
            items.append({
                "event_id": row["event_id"],
                "tenant_id": row["tenant_id"],
                "event_type": row["event_type"],
                "payload": payload,
                "created_at": row["created_at"],
            })
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    # ---- Pack3 Phase 6: Prompt and model registry ----
    def prompt_create(
        self,
        tenant_id: str,
        name: str,
        version: str,
        body: str,
        owner: str = "system",
    ) -> str:
        """Create a prompt; returns id."""
        prompt_id = str(uuid.uuid4())
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO prompts (id, tenant_id, name, version, body, owner, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (prompt_id, tenant_id, name, version, body, owner, _now()),
            )
        return prompt_id

    def prompt_get(self, tenant_id: str, prompt_id: str) -> Optional[Dict[str, Any]]:
        """Get prompt by id (tenant-scoped or fallback to default tenant for 'default')."""
        with self._conn() as conn:
            r = conn.execute(
                "SELECT id, tenant_id, name, version, body, owner, created_at FROM prompts WHERE id = ?",
                (prompt_id,),
            ).fetchone()
            if not r:
                return None
            if r["tenant_id"] != tenant_id and r["tenant_id"] != "default":
                return None
            return dict(r)

    def prompt_list(self, tenant_id: str) -> List[Dict[str, Any]]:
        """List prompts for tenant; include default tenant's 'default' if tenant has none."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, tenant_id, name, version, body, owner, created_at FROM prompts WHERE tenant_id = ? OR (tenant_id = 'default' AND id = 'default') ORDER BY created_at DESC",
                (tenant_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def model_config_create(
        self,
        tenant_id: str,
        version: str,
        model_id: str,
        params_json: Dict[str, Any],
        created_at: Optional[str] = None,
    ) -> str:
        """Create a model config; returns id."""
        config_id = str(uuid.uuid4())
        now = created_at or _now()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO model_configs (id, tenant_id, version, model_id, params_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (config_id, tenant_id, version, model_id, json.dumps(params_json or {}), now),
            )
        return config_id

    def model_config_get(self, tenant_id: str, config_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            r = conn.execute(
                "SELECT id, tenant_id, version, model_id, params_json, created_at FROM model_configs WHERE id = ?",
                (config_id,),
            ).fetchone()
            if not r:
                return None
            if r["tenant_id"] != tenant_id and r["tenant_id"] != "default":
                return None
            out = dict(r)
            if r["params_json"]:
                out["params"] = json.loads(r["params_json"]) if isinstance(r["params_json"], str) else r["params_json"]
            return out

    def model_config_list(self, tenant_id: str) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, tenant_id, version, model_id, params_json, created_at FROM model_configs WHERE tenant_id = ? OR tenant_id = 'default' ORDER BY created_at DESC",
                (tenant_id,),
            ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                if r["params_json"]:
                    d["params"] = json.loads(r["params_json"]) if isinstance(r["params_json"], str) else r["params_json"]
                result.append(d)
            return result

    def turn_provenance_add(
        self,
        tenant_id: str,
        message_id: str,
        prompt_id: str,
        model_config_id: str,
        sampling_params: Dict[str, Any],
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO turn_provenance (message_id, tenant_id, prompt_id, model_config_id, sampling_params_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (message_id, tenant_id, prompt_id, model_config_id, json.dumps(sampling_params or {}), _now()),
            )

    def turn_provenance_get(self, tenant_id: str, message_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            r = conn.execute(
                "SELECT message_id, prompt_id, model_config_id, sampling_params_json, created_at FROM turn_provenance WHERE tenant_id = ? AND message_id = ?",
                (tenant_id, message_id),
            ).fetchone()
            if not r:
                return None
            d = dict(r)
            if r["sampling_params_json"]:
                d["sampling_params"] = json.loads(r["sampling_params_json"]) if isinstance(r["sampling_params_json"], str) else r["sampling_params_json"]
            return d

    def quota_get(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Pack4: Get tenant quota limits. Returns None if not set (no limits)."""
        with self._conn() as conn:
            r = conn.execute(
                "SELECT limits_json FROM tenant_quotas WHERE tenant_id = ?",
                (tenant_id,),
            ).fetchone()
            if not r or not r["limits_json"]:
                return None
            return json.loads(r["limits_json"]) if isinstance(r["limits_json"], str) else r["limits_json"]

    def quota_set(self, tenant_id: str, limits: Dict[str, Any]) -> None:
        """Pack4: Set tenant quota limits. Idempotent upsert."""
        now = _now()
        limits_json = json.dumps(limits)
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO tenant_quotas (tenant_id, limits_json, updated_at) VALUES (?, ?, ?)
                   ON CONFLICT(tenant_id) DO UPDATE SET limits_json = excluded.limits_json, updated_at = excluded.updated_at""",
                (tenant_id, limits_json, now),
            )

    def usage_get(self, tenant_id: str) -> Dict[str, Any]:
        """Pack4: Get tenant usage counters. Returns empty dict if none."""
        with self._conn() as conn:
            r = conn.execute(
                "SELECT counters_json FROM tenant_usage WHERE tenant_id = ?",
                (tenant_id,),
            ).fetchone()
            if not r or not r["counters_json"]:
                return {}
            return json.loads(r["counters_json"]) if isinstance(r["counters_json"], str) else r["counters_json"]

    def usage_set(self, tenant_id: str, counters: Dict[str, Any]) -> None:
        """Pack4: Set tenant usage counters. Idempotent upsert inside transaction."""
        now = _now()
        counters_json = json.dumps(counters)
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO tenant_usage (tenant_id, counters_json, updated_at) VALUES (?, ?, ?)
                   ON CONFLICT(tenant_id) DO UPDATE SET counters_json = excluded.counters_json, updated_at = excluded.updated_at""",
                (tenant_id, counters_json, now),
            )

    def get_tenant_id_by_hostname(self, hostname: str) -> Optional[str]:
        """Pack 13: Resolve tenant_id from hostname via tenant_domains. Returns None if unknown."""
        if not hostname or not hostname.strip():
            return None
        host = hostname.strip().lower().split(":")[0]
        with self._conn() as conn:
            r = conn.execute(
                "SELECT tenant_id FROM tenant_domains WHERE hostname = ?",
                (host,),
            ).fetchone()
            return r["tenant_id"] if r else None

    def get_tenant_settings(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Pack 13: Get tenant_settings row for branding and approval policy. Returns None if not found."""
        with self._conn() as conn:
            r = conn.execute(
                """SELECT tenant_id, display_name, status, logo_artifact_id, theme_json, support_links_json, updated_at,
                          COALESCE(first_turn_approval_required, 0) AS first_turn_approval_required,
                          COALESCE(auto_approve_kinds_json, '[]') AS auto_approve_kinds_json,
                          COALESCE(approval_rules_json, '[]') AS approval_rules_json
                   FROM tenant_settings WHERE tenant_id = ?""",
                (tenant_id,),
            ).fetchone()
            if not r:
                return None
            out = dict(r)
            if r["theme_json"]:
                out["theme"] = json.loads(r["theme_json"]) if isinstance(r["theme_json"], str) else (r["theme_json"] or {})
            else:
                out["theme"] = {}
            if r["support_links_json"]:
                out["support_links"] = json.loads(r["support_links_json"]) if isinstance(r["support_links_json"], str) else (r["support_links_json"] or [])
            else:
                out["support_links"] = []
            j = r["auto_approve_kinds_json"] or "[]"
            out["auto_approve_kinds"] = json.loads(j) if isinstance(j, str) else (j if isinstance(j, list) else [])
            rules = r["approval_rules_json"] or "[]"
            out["approval_rules"] = json.loads(rules) if isinstance(rules, str) else (rules if isinstance(rules, list) else [])
            return out

    def tenant_settings_upsert(
        self,
        tenant_id: str,
        display_name: Optional[str] = None,
        status: Optional[str] = None,
        logo_artifact_id: Optional[str] = None,
        theme_json: Optional[Dict[str, Any]] = None,
        support_links_json: Optional[List[Any]] = None,
        first_turn_approval_required: Optional[bool] = None,
        auto_approve_kinds: Optional[List[str]] = None,
        approval_rules: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Pack 13: Upsert tenant_settings. Pass None to leave field unchanged (for partial update)."""
        with self._conn() as conn:
            existing = conn.execute(
                """SELECT display_name, status, logo_artifact_id, theme_json, support_links_json,
                          first_turn_approval_required, auto_approve_kinds_json, approval_rules_json FROM tenant_settings WHERE tenant_id = ?""",
                (tenant_id,),
            ).fetchone()
            now = _now()
            if existing:
                disp = display_name if display_name is not None else existing["display_name"]
                st = status if status is not None else existing["status"]
                logo = logo_artifact_id if logo_artifact_id is not None else existing["logo_artifact_id"]
                th = json.dumps(theme_json) if theme_json is not None else (existing["theme_json"] or "{}")
                sup = json.dumps(support_links_json) if support_links_json is not None else (existing["support_links_json"] or "[]")
                ft = 1 if first_turn_approval_required is True else (0 if first_turn_approval_required is False else (existing["first_turn_approval_required"] or 0))
                ak = json.dumps(auto_approve_kinds) if auto_approve_kinds is not None else (existing["auto_approve_kinds_json"] or "[]")
                ar = json.dumps(approval_rules) if approval_rules is not None else (existing["approval_rules_json"] or "[]")
                conn.execute(
                    """UPDATE tenant_settings SET display_name = ?, status = ?, logo_artifact_id = ?, theme_json = ?, support_links_json = ?,
                       first_turn_approval_required = ?, auto_approve_kinds_json = ?, approval_rules_json = ?, updated_at = ? WHERE tenant_id = ?""",
                    (disp, st, logo, th, sup, ft, ak, ar, now, tenant_id),
                )
            else:
                disp = display_name or ""
                st = status or "active"
                logo = logo_artifact_id
                th = json.dumps(theme_json) if theme_json is not None else "{}"
                sup = json.dumps(support_links_json) if support_links_json is not None else "[]"
                ft = 1 if first_turn_approval_required is True else 0
                ak = json.dumps(auto_approve_kinds) if auto_approve_kinds is not None else "[]"
                ar = json.dumps(approval_rules) if approval_rules is not None else "[]"
                conn.execute(
                    """INSERT INTO tenant_settings (tenant_id, display_name, status, logo_artifact_id, theme_json, support_links_json, first_turn_approval_required, auto_approve_kinds_json, approval_rules_json, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (tenant_id, disp, st, logo, th, sup, ft, ak, ar, now),
                )

    def tenant_domain_add(self, hostname: str, tenant_id: str, verified: bool = False) -> None:
        """Pack 13: Add or replace tenant_domains row."""
        host = hostname.strip().lower().split(":")[0]
        now = _now()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO tenant_domains (hostname, tenant_id, verified, created_at)
                   VALUES (?, ?, ?, ?) ON CONFLICT(hostname) DO UPDATE SET tenant_id = excluded.tenant_id, verified = excluded.verified""",
                (host, tenant_id, 1 if verified else 0, now),
            )

    def tenant_domain_get(self, hostname: str) -> Optional[Dict[str, Any]]:
        """Pack 13: Get tenant_domains row by hostname."""
        host = hostname.strip().lower().split(":")[0]
        with self._conn() as conn:
            r = conn.execute(
                "SELECT hostname, tenant_id, verified, created_at FROM tenant_domains WHERE hostname = ?",
                (host,),
            ).fetchone()
            if not r:
                return None
            return {"hostname": r["hostname"], "tenant_id": r["tenant_id"], "verified": bool(r["verified"]), "created_at": r["created_at"]}

    def tenant_domains_list(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Pack 13: List domains for a tenant."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT hostname, tenant_id, verified, created_at FROM tenant_domains WHERE tenant_id = ?",
                (tenant_id,),
            ).fetchall()
            return [{"hostname": r["hostname"], "tenant_id": r["tenant_id"], "verified": bool(r["verified"]), "created_at": r["created_at"]} for r in rows]

    def tenant_domain_remove(self, hostname: str) -> bool:
        """Pack 13: Remove a tenant_domains row. Returns True if a row was deleted."""
        host = hostname.strip().lower().split(":")[0]
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM tenant_domains WHERE hostname = ?", (host,))
            return cur.rowcount > 0

    def tenant_key_create(self, tenant_id: str) -> Tuple[str, str]:
        """Pack 13: Create API key for tenant. Returns (raw_key, key_id). Raw key shown only once."""
        raw_key = "hg_" + secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        key_id = str(uuid.uuid4())
        now = _now()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO tenant_api_keys (id, tenant_id, key_hash, created_at) VALUES (?, ?, ?, ?)",
                (key_id, tenant_id, key_hash, now),
            )
        return (raw_key, key_id)

    def tenant_key_lookup(self, api_key: str) -> Optional[str]:
        """Pack 13: Resolve tenant_id from API key by hash lookup. Returns None if not found."""
        if not api_key or len(api_key) < 10:
            return None
        key_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
        with self._conn() as conn:
            r = conn.execute(
                "SELECT tenant_id FROM tenant_api_keys WHERE key_hash = ?",
                (key_hash,),
            ).fetchone()
            return r["tenant_id"] if r else None

    def tenant_settings_list_ids(self) -> List[str]:
        """Pack 13: List tenant_ids that have tenant_settings (for superadmin list)."""
        with self._conn() as conn:
            rows = conn.execute("SELECT tenant_id FROM tenant_settings ORDER BY tenant_id", ()).fetchall()
            return [r["tenant_id"] for r in rows]

    def tenant_list(self) -> List[str]:
        """Pack3 Phase 7: List distinct tenant_ids that have chats (for retention job)."""
        with self._conn() as conn:
            rows = conn.execute("SELECT DISTINCT tenant_id FROM chats", ()).fetchall()
            return [r["tenant_id"] for r in rows]

    def retention_prune(self, tenant_id: str, cutoff_iso: str) -> Dict[str, int]:
        """Pack3 Phase 7: Delete chats (and related rows) where updated_at < cutoff_iso. Returns counts."""
        counts: Dict[str, int] = {}
        with self._conn() as conn:
            old_chats = conn.execute(
                "SELECT chat_id FROM chats WHERE tenant_id = ? AND updated_at < ?",
                (tenant_id, cutoff_iso),
            ).fetchall()
            chat_ids = [r["chat_id"] for r in old_chats]
            if not chat_ids:
                return {"chats": 0, "messages": 0, "events": 0, "agents": 0, "turn_provenance": 0, "approval_chat_lock": 0}
            placeholders = ",".join("?" * len(chat_ids))
            cur = conn.execute(
                f"DELETE FROM turn_provenance WHERE tenant_id = ? AND message_id IN (SELECT message_id FROM messages WHERE tenant_id = ? AND chat_id IN ({placeholders}))",
                (tenant_id, tenant_id, *chat_ids),
            )
            counts["turn_provenance"] = cur.rowcount
            cur = conn.execute(
                f"DELETE FROM messages WHERE tenant_id = ? AND chat_id IN ({placeholders})",
                (tenant_id, *chat_ids),
            )
            counts["messages"] = cur.rowcount
            cur = conn.execute(
                f"DELETE FROM events WHERE tenant_id = ? AND chat_id IN ({placeholders})",
                (tenant_id, *chat_ids),
            )
            counts["events"] = cur.rowcount
            cur = conn.execute(
                f"DELETE FROM agents WHERE tenant_id = ? AND chat_id IN ({placeholders})",
                (tenant_id, *chat_ids),
            )
            counts["agents"] = cur.rowcount
            cur = conn.execute(
                f"DELETE FROM approval_chat_lock WHERE tenant_id = ? AND chat_id IN ({placeholders})",
                (tenant_id, *chat_ids),
            )
            counts["approval_chat_lock"] = cur.rowcount
            cur = conn.execute(
                "DELETE FROM chats WHERE tenant_id = ? AND updated_at < ?",
                (tenant_id, cutoff_iso),
            )
            counts["chats"] = cur.rowcount
        return counts

    def tenant_delete(self, tenant_id: str) -> Dict[str, Any]:
        """Pack3 Phase 7: Hard delete all tenant data; write tombstone to audit. Returns counts deleted."""
        from hg_gateway.bundle import get_bundles_root
        counts: Dict[str, int] = {}
        with self._conn() as conn:
            for table, col in [
                ("messages", "tenant_id"),
                ("agents", "tenant_id"),
                ("events", "tenant_id"),
                ("chats", "tenant_id"),
            ]:
                cur = conn.execute(f"DELETE FROM {table} WHERE {col} = ?", (tenant_id,))
                counts[table] = cur.rowcount
            cur = conn.execute("DELETE FROM approval_chat_lock WHERE approval_id IN (SELECT id FROM approvals WHERE tenant_id = ?)", (tenant_id,))
            counts["approval_chat_lock"] = cur.rowcount
            cur = conn.execute("DELETE FROM approvals WHERE tenant_id = ?", (tenant_id,))
            counts["approvals"] = cur.rowcount
            for table in ["idempotency_records", "tool_effect_ledger", "turn_provenance", "entity_summaries"]:
                cur = conn.execute(f"DELETE FROM {table} WHERE tenant_id = ?", (tenant_id,))
                counts[table] = cur.rowcount
            for table in ["prompts", "model_configs"]:
                cur = conn.execute(f"DELETE FROM {table} WHERE tenant_id = ?", (tenant_id,))
                counts[table] = cur.rowcount
            cur = conn.execute("DELETE FROM probe_results WHERE run_id IN (SELECT run_id FROM probe_runs WHERE tenant_id = ?)", (tenant_id,))
            counts["probe_results"] = cur.rowcount
            cur = conn.execute("DELETE FROM probe_runs WHERE tenant_id = ?", (tenant_id,))
            counts["probe_runs"] = cur.rowcount
            for table in ["stepup_secrets", "stepup_challenges"]:
                try:
                    cur = conn.execute(f"DELETE FROM {table} WHERE tenant_id = ?", (tenant_id,))
                    counts[table] = cur.rowcount
                except Exception:
                    pass
            for table in ["tenant_quotas", "tenant_usage"]:
                cur = conn.execute(f"DELETE FROM {table} WHERE tenant_id = ?", (tenant_id,))
                counts[table] = cur.rowcount
            cur = conn.execute("DELETE FROM tenant_domains WHERE tenant_id = ?", (tenant_id,))
            counts["tenant_domains"] = cur.rowcount
            cur = conn.execute("DELETE FROM tenant_settings WHERE tenant_id = ?", (tenant_id,))
            counts["tenant_settings"] = cur.rowcount
            cur = conn.execute("DELETE FROM tenant_api_keys WHERE tenant_id = ?", (tenant_id,))
            counts["tenant_api_keys"] = cur.rowcount
            conn.execute(
                "INSERT INTO audit_events (tenant_id, event_type, payload, created_at) VALUES (?, ?, ?, ?)",
                (tenant_id, "tenant_deleted", json.dumps({"deleted_at": _now(), "counts": counts}), _now()),
            )
        root = get_bundles_root(tenant_id)
        tenant_dir = root.parent if root.exists() else root
        import shutil
        if tenant_dir.exists():
            shutil.rmtree(tenant_dir, ignore_errors=True)
            counts["filesystem_deleted"] = 1
        return counts


def _message_row_to_dict(r: Any) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "message_id": r["message_id"],
        "chat_id": r["chat_id"],
        "role": r["role"],
        "created_at": r["created_at"],
        "content": r["content"],
    }
    if r["agent_id"]:
        d["agent_id"] = r["agent_id"]
    if r["tool_name"]:
        d["tool_name"] = r["tool_name"]
    if r["tool_payload"] is not None:
        d["tool_payload"] = json.loads(r["tool_payload"]) if isinstance(r["tool_payload"], str) else r["tool_payload"]
    if r["tool_result"] is not None:
        d["tool_result"] = json.loads(r["tool_result"]) if isinstance(r["tool_result"], str) else r["tool_result"]
    if r["approvals_required"] is not None:
        d["approvals_required"] = bool(r["approvals_required"])
    return d


