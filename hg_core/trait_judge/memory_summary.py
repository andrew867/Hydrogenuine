"""
Memory summary pipeline for trait judge: recent/salient memories -> short summary, key facts, conflicts, evidence ids.
Supports on-demand summary for entity_id; cache in entity_summaries table.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Max words for short summary (spec: <= 200 words)
MAX_SUMMARY_WORDS = 200


def _select_memories(entity_id: str, workspace_root: Optional[Path] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Select recent and salient memories for the entity. Uses workspace memory dir if present.
    Returns list of { id, content, ts, importance } sorted by recency then importance.
    """
    memories: List[Dict[str, Any]] = []
    root = workspace_root or Path.cwd()
    # Agent memory dir pattern: memory/automation/automation-<agent_id> or memory/<entity_id>
    for candidate in [root / "memory" / "automation" / f"automation-{entity_id}", root / "memory" / entity_id]:
        if not candidate.is_dir():
            continue
        summary_7d = candidate / "summary_7d.json"
        if summary_7d.exists():
            try:
                data = json.loads(summary_7d.read_text(encoding="utf-8"))
                days = (data.get("days") or [])[-7:]
                for i, d in enumerate(days):
                    text = (d.get("summary_text") or "").strip()
                    if text:
                        mem_id = hashlib.sha256(f"{entity_id}:7d:{i}:{d.get('date','')}".encode()).hexdigest()[:16]
                        memories.append({
                            "id": mem_id,
                            "content": text[:500],
                            "ts": d.get("date", ""),
                            "importance": 0.8 - (i * 0.05),
                        })
            except Exception as e:
                logger.debug("summary_7d read failed: %s", e)
        for path in sorted(candidate.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]:
            try:
                content = path.read_text(encoding="utf-8").strip()[:800]
                if content:
                    mem_id = hashlib.sha256(f"{entity_id}:{path.name}".encode()).hexdigest()[:16]
                    memories.append({
                        "id": mem_id,
                        "content": content,
                        "ts": path.stem,
                        "importance": 0.5,
                    })
            except Exception:
                pass
        break
    # Sort by ts desc then importance desc; cap
    memories.sort(key=lambda m: (m.get("ts") or "", -(m.get("importance") or 0)), reverse=True)
    return memories[:limit]


def _rule_based_summary(memories: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build summary_text, key_facts, conflicts, evidence_ids without LLM."""
    evidence_ids = [m.get("id", "") for m in memories if m.get("id")]
    contents = [m.get("content", "").strip() for m in memories if m.get("content")]
    summary_text = " ".join(contents)[: (MAX_SUMMARY_WORDS * 6)]  # rough char cap
    words = summary_text.split()
    if len(words) > MAX_SUMMARY_WORDS:
        summary_text = " ".join(words[:MAX_SUMMARY_WORDS])
    key_facts: List[str] = []
    for c in contents[:10]:
        s = c.strip()
        if len(s) > 15:
            key_facts.append(s[:120] + ("..." if len(s) > 120 else ""))
    conflicts: List[str] = []  # placeholder; could detect contradictions with simple heuristics
    return {
        "summary_text": summary_text,
        "key_facts": key_facts,
        "conflicts": conflicts,
        "evidence_ids": evidence_ids,
    }


def build_memory_summary(
    entity_id: str,
    workspace_root: Optional[Path] = None,
    use_llm: bool = False,
) -> Dict[str, Any]:
    """
    Build memory summary for entity_id. Returns dict with summary_text, key_facts, conflicts, evidence_ids.
    Uses rule-based summary; if use_llm and LLM available can enhance (optional).
    """
    memories = _select_memories(entity_id, workspace_root)
    result = _rule_based_summary(memories)
    if use_llm:
        try:
            from hg_llm import get_default_registry, CompletionRequest
            reg = get_default_registry()
            req = CompletionRequest(
                messages=[{"role": "user", "content": f"Summarize in under {MAX_SUMMARY_WORDS} words, bullet key facts:\n\n{result['summary_text'][:2000]}"}],
                model="openai/gpt-4o-mini",
                max_tokens=400,
                temperature=0.3,
            )
            resp = reg.complete(req)
            if resp and resp.content:
                result["summary_text"] = resp.content.strip()[: (MAX_SUMMARY_WORDS * 6)]
        except Exception as e:
            logger.debug("LLM summary fallback: %s", e)
    return result


def get_memory_summary_for_entity(
    entity_id: str,
    workspace_root: Optional[Path] = None,
    cache_get: Optional[Any] = None,
    cache_set: Optional[Any] = None,
    use_llm: bool = False,
) -> Dict[str, Any]:
    """
    Get memory summary for entity: use cache if fresh, else build and optionally cache.
    cache_get(entity_id) -> { summary_text, key_facts, conflicts, evidence_ids, updated_at } or None.
    cache_set(entity_id, payload) -> None.
    Returns { summary_text, key_facts, conflicts, evidence_ids, updated_at }.
    """
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    if cache_get:
        try:
            cached = cache_get(entity_id)
            if cached and isinstance(cached, dict):
                evidence_hash = hashlib.sha256(json.dumps(cached.get("evidence_ids", []), sort_keys=True).encode()).hexdigest()[:16]
                current = build_memory_summary(entity_id, workspace_root, use_llm=False)
                current_hash = hashlib.sha256(json.dumps(current.get("evidence_ids", []), sort_keys=True).encode()).hexdigest()[:16]
                if evidence_hash == current_hash and cached.get("updated_at"):
                    return {**cached, "updated_at": cached["updated_at"]}
        except Exception as e:
            logger.debug("cache_get failed: %s", e)
    result = build_memory_summary(entity_id, workspace_root, use_llm=use_llm)
    out = {
        "summary_text": result["summary_text"],
        "key_facts": result["key_facts"],
        "conflicts": result["conflicts"],
        "evidence_ids": result["evidence_ids"],
        "updated_at": now,
    }
    if cache_set:
        try:
            cache_set(entity_id, out)
        except Exception as e:
            logger.debug("cache_set failed: %s", e)
    return out
