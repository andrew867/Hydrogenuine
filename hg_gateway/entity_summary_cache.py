"""Cache for trait judge entity memory summaries (entity_summaries table)."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from hg_gateway.db import get_connection, _get_db_path


def get_entity_summary(entity_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Load cached summary for entity_id. Returns dict with summary_text, key_facts, conflicts, evidence_ids, updated_at or None."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT summary_text, key_facts, conflicts, evidence_ids, updated_at FROM entity_summaries WHERE entity_id = ?",
            (entity_id,),
        ).fetchone()
        if not row:
            return None
        try:
            key_facts = json.loads(row["key_facts"]) if row["key_facts"] else []
            conflicts = json.loads(row["conflicts"]) if row["conflicts"] else []
            evidence_ids = json.loads(row["evidence_ids"]) if row["evidence_ids"] else []
        except json.JSONDecodeError:
            key_facts = []
            conflicts = []
            evidence_ids = []
        return {
            "summary_text": row["summary_text"] or "",
            "key_facts": key_facts,
            "conflicts": conflicts,
            "evidence_ids": evidence_ids,
            "updated_at": row["updated_at"] or "",
        }


def set_entity_summary(entity_id: str, payload: Dict[str, Any], db_path: Optional[str] = None) -> None:
    """Write summary to cache. payload: summary_text, key_facts, conflicts, evidence_ids, updated_at."""
    with get_connection(db_path) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO entity_summaries
               (entity_id, summary_text, key_facts, conflicts, evidence_ids, evidence_hash, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                entity_id,
                payload.get("summary_text", ""),
                json.dumps(payload.get("key_facts", [])),
                json.dumps(payload.get("conflicts", [])),
                json.dumps(payload.get("evidence_ids", [])),
                None,
                payload.get("updated_at", ""),
            ),
        )
