"""
Feedback Tracker for Agent Feedback Acknowledgment

Handles reading, acknowledging, and persisting overseer feedback to agent memory.
Uses hg_lib.config for paths. No skills.* imports.
"""

import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from hg_lib.config import get_workspace_root, get_automation_memory_dir


def find_workspace_root() -> Path:
    """Find the Hydrogenuine workspace root directory. Prefer hg_lib.config."""
    return get_workspace_root()


def get_agent_memory_dir(agent_id: str) -> Path:
    """Get the memory directory path for an agent."""
    return get_automation_memory_dir(agent_id)


def read_new_feedback(agent_id: str, date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Read all feedback with status "new" from agent's daily memory file.

    Args:
        agent_id: Agent identifier (e.g., "moltbook-auto-post")
        date: Date string in YYYY-MM-DD format (defaults to today)

    Returns:
        List of feedback dictionaries with keys: timestamp, severity, issue, description, recommendations, status
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    memory_dir = get_agent_memory_dir(agent_id)
    memory_file = memory_dir / f"{date}.md"

    if not memory_file.exists():
        return []

    try:
        content = memory_file.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"Warning: Could not read memory file {memory_file}: {type(e).__name__}: {str(e)}", file=sys.stderr)
        return []

    feedback_items = []
    feedback_pattern = r'## Overseer Feedback - (\d{2}:\d{2})\s*\n(.*?)(?=\n## |\Z)'
    matches = re.finditer(feedback_pattern, content, re.DOTALL)

    for match in matches:
        timestamp_str = match.group(1)
        feedback_content = match.group(2)

        status_match = re.search(r'\*\*Status:\*\* (.+)', feedback_content)
        if not status_match or status_match.group(1).strip().lower() != "new":
            continue

        severity_match = re.search(r'\*\*Severity:\*\* (.+)', feedback_content)
        severity = severity_match.group(1).strip() if severity_match else "medium"

        issue_match = re.search(r'\*\*Issue:\*\* (.+)', feedback_content)
        issue_type_match = re.search(r'\*\*Issue Type:\*\* (.+)', feedback_content)
        description_match = re.search(r'\*\*Description:\*\* (.+)', feedback_content)

        issue = issue_match.group(1).strip() if issue_match else ""
        issue_type = issue_type_match.group(1).strip() if issue_type_match else ""
        description = description_match.group(1).strip() if description_match else issue

        recommendations = []
        rec_match = re.search(r'\*\*(?:Recommendations?|Recommended Actions?):\*\*\s*\n((?:- .+\n?)+)', feedback_content)
        if rec_match:
            rec_lines = rec_match.group(1).strip().split('\n')
            for line in rec_lines:
                if line.strip().startswith('-'):
                    recommendations.append(line.strip()[2:].strip())

        feedback_match = re.search(r'\*\*Feedback:\*\*\s*\n(.+?)(?=\n\*\*|$)', feedback_content, re.DOTALL)
        message = feedback_match.group(1).strip() if feedback_match else ""

        feedback_id = f"{date}-{timestamp_str}-{issue_type or issue or 'general'}"
        feedback_id = re.sub(r'[^\w\-]', '_', feedback_id)

        feedback_items.append({
            "feedback_id": feedback_id,
            "timestamp": f"{date}T{timestamp_str}:00Z",
            "severity": severity,
            "issue_type": issue_type or issue or "general",
            "issue": issue,
            "description": description,
            "message": message,
            "recommendations": recommendations,
            "status": "new",
            "raw_content": feedback_content
        })

    return feedback_items


def update_feedback_status(agent_id: str, feedback_id: str, action_taken: str, date: Optional[str] = None) -> bool:
    """Update feedback status from "new" to "acknowledged" in memory file."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    memory_dir = get_agent_memory_dir(agent_id)
    memory_file = memory_dir / f"{date}.md"

    if not memory_file.exists():
        return False

    try:
        content = memory_file.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False

    parts = feedback_id.split('-')
    if len(parts) < 5:
        return False

    time_part = parts[3]
    timestamp_str = time_part.replace('_', ':')

    pattern = rf'## Overseer Feedback - {re.escape(timestamp_str)}\s*\n(.*?)(?=\n## |\Z)'
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        return False

    feedback_section = match.group(0)
    updated_section = re.sub(r'\*\*Status:\*\* new', '**Status:** acknowledged', feedback_section)

    if '**Acknowledged at:**' not in updated_section:
        ack_time = datetime.now().strftime("%H:%M:%S")
        action_line = f"\n**Acknowledged at:** {ack_time}\n**Action taken:** {action_taken}\n"
        if updated_section.rstrip().endswith('---'):
            updated_section = updated_section.rstrip()[:-3] + action_line + "---\n"
        else:
            updated_section = updated_section.rstrip() + action_line + "\n"

    content = content.replace(feedback_section, updated_section)

    try:
        memory_file.write_text(content, encoding="utf-8")
        return True
    except Exception:
        return False


def write_acknowledgment_json(agent_id: str, feedback_item: Dict[str, Any], action_taken: str, applied_in_run: bool = True) -> bool:
    """Write acknowledgment to feedback_acknowledgments.json file."""
    memory_dir = get_agent_memory_dir(agent_id)
    memory_dir.mkdir(parents=True, exist_ok=True)

    ack_file = memory_dir / "feedback_acknowledgments.json"
    acknowledgments = {"acknowledgments": [], "last_updated": ""}
    if ack_file.exists():
        try:
            with open(ack_file, 'r', encoding='utf-8') as f:
                acknowledgments = json.load(f)
        except Exception:
            pass

    feedback_id = feedback_item.get("feedback_id", "")
    existing = [a for a in acknowledgments.get("acknowledgments", []) if a.get("feedback_id") == feedback_id]

    if existing:
        existing[0].update({
            "action_taken": action_taken,
            "applied_in_this_run": applied_in_run,
            "last_updated": datetime.now().isoformat() + "Z"
        })
    else:
        ack_entry = {
            "feedback_id": feedback_id,
            "timestamp": feedback_item.get("timestamp", ""),
            "severity": feedback_item.get("severity", "medium"),
            "issue_type": feedback_item.get("issue_type", "general"),
            "acknowledged": True,
            "action_taken": action_taken,
            "applied_in_this_run": applied_in_run,
            "persisted_to_long_term": False,
            "acknowledged_at": datetime.now().isoformat() + "Z"
        }
        acknowledgments.setdefault("acknowledgments", []).append(ack_entry)

    acknowledgments["last_updated"] = datetime.now().isoformat() + "Z"

    try:
        with open(ack_file, 'w', encoding='utf-8') as f:
            json.dump(acknowledgments, f, indent=2)
        return True
    except Exception:
        return False


def persist_to_long_term_memory(agent_id: str, feedback_item: Dict[str, Any], action_taken: str) -> bool:
    """Persist acknowledged feedback to feedback_memory.md file."""
    memory_dir = get_agent_memory_dir(agent_id)
    memory_dir.mkdir(parents=True, exist_ok=True)

    feedback_memory_file = memory_dir / "feedback_memory.md"
    timestamp = feedback_item.get("timestamp", "")
    date_str = timestamp.split("T")[0] if "T" in timestamp else datetime.now().strftime("%Y-%m-%d")
    time_str = timestamp.split("T")[1].split(":")[:2] if "T" in timestamp else ["00", "00"]
    time_display = ":".join(time_str)

    existing_content = ""
    if feedback_memory_file.exists():
        try:
            existing_content = feedback_memory_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass

    feedback_id = feedback_item.get("feedback_id", "")
    if feedback_id in existing_content:
        return True

    issue_type = feedback_item.get("issue_type", "general")
    issue = feedback_item.get("issue", "") or feedback_item.get("description", "")
    severity = feedback_item.get("severity", "medium")
    recommendations = feedback_item.get("recommendations", [])

    entry = f"""
### {issue_type.replace('_', ' ').title()} Issue ({time_display})
**Severity:** {severity}
**Issue:** {issue}
**Action taken:** {action_taken}
**Status:** Acknowledged and applied
**Date acknowledged:** {datetime.now().isoformat()}Z

"""
    if recommendations:
        entry += "**Recommendations:**\n"
        for rec in recommendations:
            entry += f"- {rec}\n"
        entry += "\n"

    date_header = f"## {date_str}"
    if date_header not in existing_content:
        if existing_content:
            existing_content += f"\n{date_header}\n"
        else:
            existing_content = f"# Feedback Memory - {agent_id}\n\nThis file contains all acknowledged feedback and changes made to improve agent behavior.\n\n{date_header}\n"

    date_header_pos = existing_content.find(date_header)
    if date_header_pos != -1:
        next_section = existing_content.find("\n## ", date_header_pos + len(date_header))
        if next_section == -1:
            existing_content += entry
        else:
            existing_content = existing_content[:next_section] + entry + existing_content[next_section:]
    else:
        existing_content += entry

    try:
        feedback_memory_file.write_text(existing_content, encoding="utf-8")
        ack_file = memory_dir / "feedback_acknowledgments.json"
        if ack_file.exists():
            try:
                with open(ack_file, 'r', encoding='utf-8') as f:
                    acknowledgments = json.load(f)
                for ack in acknowledgments.get("acknowledgments", []):
                    if ack.get("feedback_id") == feedback_id:
                        ack["persisted_to_long_term"] = True
                with open(ack_file, 'w', encoding='utf-8') as f:
                    json.dump(acknowledgments, f, indent=2)
            except Exception:
                pass
        return True
    except Exception:
        return False


def acknowledge_feedback(agent_id: str, feedback_item: Dict[str, Any], action_taken: str, applied_in_run: bool = True) -> Dict[str, Any]:
    """Complete acknowledgment workflow: update status, write JSON, persist to long-term memory."""
    feedback_id = feedback_item.get("feedback_id", "")
    status_updated = update_feedback_status(agent_id, feedback_id, action_taken)
    json_written = write_acknowledgment_json(agent_id, feedback_item, action_taken, applied_in_run)
    memory_persisted = persist_to_long_term_memory(agent_id, feedback_item, action_taken)
    success = json_written
    return {
        "success": success,
        "status_updated": status_updated,
        "json_written": json_written,
        "memory_persisted": memory_persisted,
        "feedback_id": feedback_id
    }


def preserve_feedback_before_compaction(agent_id: str, memory_file_path: Path) -> bool:
    """Extract all acknowledged feedback from a memory file and ensure it's in feedback_memory.md."""
    if not memory_file_path.exists():
        return True

    try:
        content = memory_file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False

    feedback_pattern = r'## Overseer Feedback - (\d{2}:\d{2})\s*\n(.*?)(?=\n## |\Z)'
    matches = re.finditer(feedback_pattern, content, re.DOTALL)

    memory_dir = get_agent_memory_dir(agent_id)
    feedback_memory_file = memory_dir / "feedback_memory.md"

    existing_content = ""
    if feedback_memory_file.exists():
        try:
            existing_content = feedback_memory_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass

    date_str = memory_file_path.stem
    preserved_count = 0

    for match in matches:
        timestamp_str = match.group(1)
        feedback_content = match.group(2)

        feedback_id_pattern = f"{date_str}-{timestamp_str}"
        if feedback_id_pattern in existing_content:
            continue

        status_match = re.search(r'\*\*Status:\*\* (.+)', feedback_content)
        if not status_match:
            continue
        status = status_match.group(1).strip().lower()
        if status != "acknowledged":
            continue

        issue_match = re.search(r'\*\*Issue:\*\* (.+)', feedback_content)
        issue_type_match = re.search(r'\*\*Issue Type:\*\* (.+)', feedback_content)
        description_match = re.search(r'\*\*Description:\*\* (.+)', feedback_content)

        issue_type = issue_type_match.group(1).strip() if issue_type_match else ""
        issue = issue_match.group(1).strip() if issue_match else ""
        description = description_match.group(1).strip() if description_match else issue

        severity_match = re.search(r'\*\*Severity:\*\* (.+)', feedback_content)
        severity = severity_match.group(1).strip() if severity_match else "medium"

        action_match = re.search(r'\*\*Action taken:\*\* (.+)', feedback_content)
        action_taken = action_match.group(1).strip() if action_match else "Acknowledged"

        recommendations = []
        rec_match = re.search(r'\*\*(?:Recommendations?|Recommended Actions?):\*\*\s*\n((?:- .+\n?)+)', feedback_content)
        if rec_match:
            rec_lines = rec_match.group(1).strip().split('\n')
            for line in rec_lines:
                if line.strip().startswith('-'):
                    recommendations.append(line.strip()[2:].strip())

        time_display = timestamp_str
        entry_title = issue_type.replace('_', ' ').title() if issue_type else (issue or description or "General Issue")

        entry = f"""
### {entry_title} ({time_display})
**Severity:** {severity}
**Issue:** {issue or description or "N/A"}
**Action taken:** {action_taken}
**Status:** Acknowledged and applied
**Date acknowledged:** {date_str}T{timestamp_str}:00Z

"""
        if recommendations:
            entry += "**Recommendations:**\n"
            for rec in recommendations:
                entry += f"- {rec}\n"
            entry += "\n"

        date_header = f"## {date_str}"
        if date_header not in existing_content:
            if existing_content:
                existing_content += f"\n{date_header}\n"
            else:
                existing_content = f"# Feedback Memory - {agent_id}\n\nThis file contains all acknowledged feedback and changes made to improve agent behavior.\n\n{date_header}\n"

        date_header_pos = existing_content.find(date_header)
        if date_header_pos != -1:
            next_section = existing_content.find("\n## ", date_header_pos + len(date_header))
            if next_section == -1:
                existing_content += entry
            else:
                existing_content = existing_content[:next_section] + entry + existing_content[next_section:]
        else:
            existing_content += entry

        preserved_count += 1

    if preserved_count > 0:
        try:
            feedback_memory_file.write_text(existing_content, encoding="utf-8")
            return True
        except Exception:
            return False

    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: feedback_tracker.py <command> [args...]")
        print("  read-new <agent_id> [date]")
        print("  acknowledge <agent_id> <feedback_id> <action_taken>")
        sys.exit(1)
    command = sys.argv[1]
    if command == "read-new":
        if len(sys.argv) < 3:
            print("Usage: feedback_tracker.py read-new <agent_id> [date]")
            sys.exit(1)
        agent_id = sys.argv[2]
        date = sys.argv[3] if len(sys.argv) > 3 else None
        print(json.dumps(read_new_feedback(agent_id, date), indent=2))
    elif command == "acknowledge":
        print("Use acknowledge_feedback() function with full feedback_item for complete workflow")
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
