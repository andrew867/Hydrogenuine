"""
Extraction job: parse recent daily notes and suggest facts for the life/ entity graph.

Reads last K days of daily logs (YYYY-MM-DD.md), applies rule-based extraction for
durable facts (decisions, meetings, patterns), and writes to a staging file for
human/agent review before merging into life/ entities. Principle: be selective —
only suggest facts future-you would need.

Trigger: cron (e.g. daily after memory-maintenance) or optional step in memory_maintenance
when config extract_from_daily_notes is true.
"""

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# Simple patterns that often indicate a durable fact (rule-based; extend or add LLM later)
DECISION_PATTERN = re.compile(r"^(?:decision|decided|choice):\s*(.+)$", re.IGNORECASE)
MEETING_PATTERN = re.compile(r"^(?:met|meeting|spoke with|talked to)\s+(?:with\s+)?([A-Za-z][A-Za-z0-9_\s-]*?)(?:\s+about|\s+regarding|\.|$)", re.IGNORECASE)
KEY_PATTERN = re.compile(r"^(?:key|important|note):\s*(.+)$", re.IGNORECASE)
SECTION_HEADER = re.compile(r"^##\s+\d{2}:\d{2}\s*[—\-]\s*(.+)$")


def _extract_from_text(content: str, source_file: str, date_str: str) -> List[Dict[str, Any]]:
    """Extract suggested facts from one daily log's content. Returns list of suggested fact dicts."""
    suggested: List[Dict[str, Any]] = []
    lines = content.splitlines()
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped or len(line_stripped) < 10:
            continue
        m = DECISION_PATTERN.match(line_stripped)
        if m:
            suggested.append({
                "fact": m.group(1).strip()[:500],
                "category": "decision",
                "source": source_file,
                "date": date_str,
                "suggested_entity": None,
            })
            continue
        m = MEETING_PATTERN.match(line_stripped)
        if m:
            who = m.group(1).strip()[:100]
            suggested.append({
                "fact": line_stripped[:500],
                "category": "meeting",
                "source": source_file,
                "date": date_str,
                "suggested_entity": f"people/{who.replace(' ', '-').lower()}",
            })
            continue
        m = KEY_PATTERN.match(line_stripped)
        if m:
            suggested.append({
                "fact": m.group(1).strip()[:500],
                "category": "note",
                "source": source_file,
                "date": date_str,
                "suggested_entity": None,
            })
            continue
        m = SECTION_HEADER.match(line_stripped)
        if m and len(m.group(1)) > 15:
            suggested.append({
                "fact": m.group(1).strip()[:500],
                "category": "highlight",
                "source": source_file,
                "date": date_str,
                "suggested_entity": None,
            })
    return suggested


def run_extraction(
    workspace_root: Path,
    agent_id: str,
    days: int = 7,
) -> Dict[str, Any]:
    """
    Run extraction for one agent: read last `days` daily logs, suggest facts, write staging file.

    Returns:
        {"suggested": N, "staging_path": str, "errors": list}
    """
    memory_dir = workspace_root / "memory" / "automation" / f"automation-{agent_id}"
    if not memory_dir.exists():
        return {"suggested": 0, "staging_path": "", "errors": ["agent dir not found"]}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).date()
    all_suggested: List[Dict[str, Any]] = []
    errors: List[str] = []
    for f in memory_dir.iterdir():
        if not f.is_file() or f.suffix != ".md":
            continue
        name = f.name
        if not re.match(r"^\d{4}-\d{2}-\d{2}\.md$", name):
            continue
        date_str = name.replace(".md", "")
        try:
            file_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            if file_date < cutoff:
                continue
        except ValueError:
            continue
        try:
            content = f.read_text(encoding="utf-8")
        except OSError as e:
            errors.append(f"read {name}: {e}")
            continue
        suggested = _extract_from_text(content, name, date_str)
        all_suggested.extend(suggested)
    staging_path = memory_dir / "extraction_staging.json"
    try:
        staging_path.write_text(
            json.dumps({
                "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "agent_id": agent_id,
                "suggested_facts": all_suggested,
                "principle": "Be selective — only add facts future-you would need. Review before merging into life/.",
            }, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as e:
        errors.append(f"write staging: {e}")
        return {"suggested": len(all_suggested), "staging_path": "", "errors": errors}
    return {
        "suggested": len(all_suggested),
        "staging_path": str(staging_path),
        "errors": errors,
    }


def run_extraction_all_agents(
    workspace_root: Optional[Path] = None,
    days: int = 7,
) -> Dict[str, Any]:
    """Run extraction for all automation agents. Discover agents from memory/automation/."""
    from hg_memory.config import get_config
    config = get_config()
    root = Path(workspace_root) if workspace_root is not None else config.workspace_root
    automation_dir = root / "memory" / "automation"
    if not automation_dir.exists():
        return {"agents": 0, "total_suggested": 0, "per_agent": {}, "errors": []}
    per_agent: Dict[str, Dict[str, Any]] = {}
    all_errors: List[str] = []
    for d in automation_dir.iterdir():
        if not d.is_dir() or not d.name.startswith("automation-"):
            continue
        agent_id = d.name.replace("automation-", "", 1)
        result = run_extraction(root, agent_id, days=days)
        per_agent[agent_id] = result
        all_errors.extend(result.get("errors", []))
    return {
        "agents": len(per_agent),
        "total_suggested": sum(r.get("suggested", 0) for r in per_agent.values()),
        "per_agent": per_agent,
        "errors": all_errors,
    }
