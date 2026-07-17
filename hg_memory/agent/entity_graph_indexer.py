#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Index life/ directory (PARA-style) into entity/fact graph.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_gateway.shared_storage import list_agent_decisions
from hg_memory.config import get_config

from hg_memory.agent.entity_graph_db import (
    EntityGraphDatabase,
    get_entity_graph_db_path,
)


# Subdirs under life/ that map to entity types (areas/people -> people, etc.)
LIFE_ENTITY_TYPES = [
    ("areas/people", "people"),
    ("areas/companies", "companies"),
    ("resources", "resources"),
    ("projects", "projects"),
]


def _looks_like_test_noise(*parts: Any) -> bool:
    text = " ".join(_as_text(p, 400).lower() for p in parts if p is not None)
    if not text:
        return False
    patterns = (
        "integration test",
        "test action",
        "test rationale",
        "automatic recording agent id mapping",
        "testing agent id:",
        "pytest",
        "dummy",
        "sample fixture",
    )
    return any(p in text for p in patterns)


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _as_text(value: Any, max_len: int = 240) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value.strip()
    elif isinstance(value, (int, float, bool)):
        text = str(value)
    elif isinstance(value, list):
        parts = []
        for v in value:
            vv = _as_text(v, max_len=80)
            if vv:
                parts.append(vv)
        text = ", ".join(parts)
    elif isinstance(value, dict):
        # Keep context compact and readable in the graph table.
        pairs = []
        for k, v in value.items():
            val = _as_text(v, max_len=80)
            if val:
                pairs.append(f"{k}={val}")
        text = "; ".join(pairs)
    else:
        text = str(value)
    if len(text) > max_len:
        return text[: max_len - 1] + "…"
    return text


def _upsert_session_entity_with_facts(
    db: EntityGraphDatabase,
    name: str,
    path: str,
    summary: str,
    facts: List[Dict[str, Any]],
) -> Dict[str, int]:
    indexed = 0
    errors = 0
    try:
        entity_id = db.upsert_entity(
            type="session_memory",
            name=name,
            path=path,
            summary_excerpt=summary,
        )
    except Exception:
        return {"indexed": 0, "errors": 1}

    # Refresh generated facts for this synthetic entity each indexing run.
    try:
        db.delete_facts_for_entity(entity_id)
    except Exception:
        errors += 1

    seen: set[str] = set()
    for item in facts:
        fact_text = (item.get("fact") or "").strip()
        if not fact_text:
            continue
        dedupe_key = f"{item.get('category') or ''}|{fact_text}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        try:
            db.upsert_fact(
                entity_id=entity_id,
                fact=fact_text,
                category=item.get("category"),
                timestamp=item.get("timestamp"),
                source=item.get("source"),
                status="active",
                related_entities_json="[]",
            )
            indexed += 1
        except Exception:
            errors += 1
    return {"indexed": indexed, "errors": errors}


def index_session_memory(agent_dir: Path, db: EntityGraphDatabase) -> Dict[str, int]:
    """
    Populate synthetic entity/fact rows from DB-backed session memory so
    operator Entity Graph has useful data even when life/ is not curated.
    """
    total_indexed = 0
    total_errors = 0
    session_id = agent_dir.name
    agent_id = session_id.removeprefix("automation-")

    from hg_gateway.shared_storage import get_operational_state

    session_payload = get_operational_state(f"automation:session_memory:{session_id}", None)
    if isinstance(session_payload, dict):
        facts: List[Dict[str, Any]] = []
        posts = session_payload.get("posts", [])
        if isinstance(posts, list):
            for post in posts[-120:]:
                if not isinstance(post, dict):
                    continue
                title = _as_text(post.get("title") or post.get("subject"), 120)
                content = _as_text(
                    post.get("content")
                    or post.get("body")
                    or post.get("text")
                    or post.get("comment"),
                    160,
                )
                board = _as_text(post.get("board"), 32)
                thread_id = _as_text(post.get("thread_id"), 40)
                parts = [p for p in [title, content] if p]
                if not parts:
                    continue
                if _looks_like_test_noise(title, content, post.get("context"), post.get("rationale")):
                    continue
                prefix = "post"
                if board:
                    prefix += f" /{board}/"
                if thread_id:
                    prefix += f" #{thread_id}"
                facts.append(
                    {
                        "fact": f"{prefix}: {' | '.join(parts)}",
                        "category": "posts",
                        "timestamp": post.get("timestamp") or post.get("created_at"),
                        "source": "session_memory",
                    }
                )
        interactions = session_payload.get("interactions", [])
        if isinstance(interactions, list):
            for interaction in interactions[-150:]:
                text = _as_text(interaction, 180)
                if not text or _looks_like_test_noise(text):
                    continue
                facts.append(
                    {
                        "fact": f"interaction: {text}",
                        "category": "interactions",
                        "timestamp": None,
                        "source": "session_memory",
                    }
                )
        context_data = session_payload.get("context", {})
        if isinstance(context_data, dict):
            for key, value in context_data.items():
                text = _as_text(value, 220)
                if not text:
                    continue
                facts.append(
                    {
                        "fact": f"{key}: {text}",
                        "category": "context",
                        "timestamp": context_data.get("last_updated"),
                        "source": "session_memory",
                    }
                )
        recent_activity = session_payload.get("recent_activity", [])
        if isinstance(recent_activity, list):
            for entry in recent_activity[-50:]:
                text = _as_text(entry, 220)
                if not text:
                    continue
                facts.append(
                    {
                        "fact": f"recent_activity: {text}",
                        "category": "activity",
                        "timestamp": None,
                        "source": "session_memory",
                    }
                )
        summary_7d = session_payload.get("summary_7d", {})
        if isinstance(summary_7d, dict) and summary_7d:
            summary_text = _as_text(summary_7d, 240)
            if summary_text:
                facts.append(
                    {
                        "fact": f"summary_7d: {summary_text}",
                        "category": "summary",
                        "timestamp": summary_7d.get("updated_at") or summary_7d.get("last_updated"),
                        "source": "session_memory",
                    }
                )
        res = _upsert_session_entity_with_facts(
            db=db,
            name="session_memory",
            path=f"memory/automation/{session_id}",
            summary=f"{len(facts)} session memory facts",
            facts=facts,
        )
        total_indexed += res["indexed"]
        total_errors += res["errors"]

    decisions = list_agent_decisions(agent_dir.name.replace("automation-", "", 1), limit=500)
    if decisions:
        facts = []
        for d in decisions[-200:]:
            if not isinstance(d, dict):
                continue
            action = _as_text(d.get("action"), 120)
            rationale = _as_text(d.get("rationale"), 160)
            context = _as_text(d.get("context"), 180)
            if _looks_like_test_noise(action, rationale, context):
                continue
            if not action and not rationale:
                continue
            text = " | ".join(p for p in [action, rationale] if p)
            facts.append(
                {
                    "fact": f"decision: {text}",
                    "category": "decisions",
                    "timestamp": d.get("timestamp"),
                    "source": "agent_decisions",
                }
            )
        res = _upsert_session_entity_with_facts(
            db=db,
            name="decisions",
            path="memory/agent_decisions",
            summary=f"{len(facts)} decision facts",
            facts=facts,
        )
        total_indexed += res["indexed"]
        total_errors += res["errors"]

    # Capture a lightweight activity signal from recent daily notes.
    daily_facts: List[Dict[str, Any]] = []
    for md_file in sorted(agent_dir.glob("*.md"))[-5:]:
        try:
            content = md_file.read_text(encoding="utf-8")
        except OSError:
            total_errors += 1
            continue
        lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
        if not lines:
            continue
        excerpt = _as_text(" ".join(lines[:6]), 220)
        if excerpt:
            if _looks_like_test_noise(excerpt):
                continue
            daily_facts.append(
                {
                    "fact": f"{md_file.name}: {excerpt}",
                    "category": "activity",
                    "timestamp": None,
                    "source": md_file.name,
                }
            )
    if daily_facts:
        res = _upsert_session_entity_with_facts(
            db=db,
            name="activity",
            path="memory/*.md",
            summary=f"{len(daily_facts)} recent activity facts",
            facts=daily_facts,
        )
        total_indexed += res["indexed"]
        total_errors += res["errors"]

    return {"indexed": total_indexed, "errors": total_errors}


def _read_summary(entity_dir: Path) -> Optional[str]:
    summary_path = entity_dir / "summary.md"
    if not summary_path.exists():
        return None
    try:
        return summary_path.read_text(encoding="utf-8").strip()[:500]
    except OSError:
        return None


def _read_items(entity_dir: Path) -> List[Dict[str, Any]]:
    items_path = entity_dir / "items.json"
    if not items_path.exists():
        return []
    try:
        data = json.loads(items_path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "items" in data:
            return data["items"]
        return []
    except (json.JSONDecodeError, OSError):
        return []


def index_life_dir(
    life_dir: Path,
    db: EntityGraphDatabase,
    base_path: str,
) -> Dict[str, int]:
    """
    Scan life_dir for entity dirs (areas/people/<name>, etc.), read summary.md and items.json,
    upsert entity and facts. base_path is the relative path prefix (e.g. "life/areas/people").
    """
    indexed = 0
    errors = 0
    for entity_dir in life_dir.iterdir():
        if not entity_dir.is_dir():
            continue
        name = entity_dir.name
        if name.startswith("."):
            continue
        rel_path = f"{base_path}/{name}".replace("\\", "/")
        summary = _read_summary(entity_dir)
        entity_type = base_path.split("/")[-1] if "/" in base_path else "entity"
        try:
            entity_id = db.upsert_entity(
                type=entity_type,
                name=name,
                path=rel_path,
                summary_excerpt=summary,
            )
        except Exception:
            errors += 1
            continue
        db.delete_facts_for_entity(entity_id)
        for item in _read_items(entity_dir):
            if not isinstance(item, dict):
                continue
            fact_text = item.get("fact") or item.get("content") or str(item)
            if not fact_text.strip():
                continue
            try:
                db.upsert_fact(
                    entity_id=entity_id,
                    fact=fact_text,
                    category=item.get("category"),
                    timestamp=item.get("timestamp") or item.get("date"),
                    source=item.get("source"),
                    status=item.get("status"),
                    related_entities_json=json.dumps(
                        item.get("relatedEntities", item.get("related_entities", []))
                    )
                    if item.get("relatedEntities") or item.get("related_entities")
                    else None,
                )
                indexed += 1
            except Exception:
                errors += 1
    return {"indexed": indexed, "errors": errors}


def run_entity_graph_indexer(
    agent_id: str,
    workspace_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Run entity graph indexer for one agent. Scans memory/automation/automation-<agent>/life/
    and upserts into agent_memory.db (entity/fact tables).
    """
    config = get_config()
    root = Path(workspace_root) if workspace_root is not None else config.workspace_root
    life_dir = root / "memory" / "automation" / f"automation-{agent_id}" / "life"
    db_path = get_entity_graph_db_path(root, agent_id)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = EntityGraphDatabase(str(db_path))
    total_indexed = 0
    total_errors = 0
    for subdir, _entity_type in LIFE_ENTITY_TYPES:
        path = life_dir
        for part in subdir.split("/"):
            path = path / part
        base_path = "life/" + subdir
        if not path.exists():
            continue
        result = index_life_dir(path, db, base_path)
        total_indexed += result["indexed"]
        total_errors += result["errors"]
    # Always derive graph facts from DB-backed session memory so operator graphs are
    # populated even when life/ is not curated.
    session_result = index_session_memory(
        root / "memory" / "automation" / f"automation-{agent_id}",
        db,
    )
    total_indexed += session_result["indexed"]
    total_errors += session_result["errors"]
    return {"indexed": total_indexed, "errors": total_errors}
