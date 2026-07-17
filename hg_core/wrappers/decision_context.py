"""
Decision Context Metadata Helper

Records decision rationale and intent metadata alongside actions.
Uses hg_lib.config for paths. No skills.* imports.
"""

import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from hg_lib.config import get_workspace_root, get_automation_memory_dir

from hg_gateway.shared_storage import append_agent_decision, list_agent_decisions


def record_decision(
    agent_id: str,
    action: str,
    rationale: str,
    alternatives: Optional[List[str]] = None,
    tradeoffs: Optional[str] = None,
    context: Optional[str] = None,
    outcome: Optional[str] = None,
    date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Record a decision with rationale to the agent's memory file.

    Args:
        agent_id: Agent identifier (e.g., "fourclaw-engage")
        action: What was done
        rationale: Why this decision was made
        alternatives: Other options considered (optional)
        tradeoffs: What was sacrificed/gained (optional)
        context: Relevant background information (optional)
        outcome: Expected vs actual result (optional)
        date: Date string (YYYY-MM-DD), defaults to today

    Returns:
        Dictionary with the recorded decision data
    """
    memory_dir = get_automation_memory_dir(agent_id)
    memory_dir.mkdir(parents=True, exist_ok=True)

    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    memory_file = memory_dir / f"{date}.md"

    # Create decision context section
    timestamp = datetime.now().strftime("%H:%M")

    decision_section = f"""

## Decision Context - {timestamp}

**Action:** {action}
**Rationale:** {rationale}
"""

    if alternatives:
        alt_text = "\n".join([f"- {alt}" for alt in alternatives])
        decision_section += f"**Alternatives Considered:**\n{alt_text}\n"

    if tradeoffs:
        decision_section += f"**Trade-offs:** {tradeoffs}\n"

    if context:
        decision_section += f"**Context:** {context}\n"

    if outcome:
        decision_section += f"**Outcome:** {outcome}\n"

    decision_section += "\n---\n"

    # Append to memory file
    try:
        with open(memory_file, "a", encoding="utf-8") as f:
            f.write(decision_section)
    except IOError as e:
        return {"success": False, "error": str(e)}

    decision_id = uuid.uuid4().hex[:12]
    decision_record = {
        "decision_id": decision_id,
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "rationale": rationale,
        "alternatives": alternatives or [],
        "tradeoffs": tradeoffs,
        "context": context,
        "outcome": outcome,
    }

    try:
        append_agent_decision(
            decision_id=decision_id,
            agent_id=agent_id,
            timestamp=decision_record["timestamp"],
            action=action,
            rationale=rationale,
            alternatives=alternatives or [],
            tradeoffs=tradeoffs,
            context=context,
            outcome=outcome,
        )
    except Exception:
        pass

    # Sticky Reality ledger: emit DECISION_COMMITTED for facts↔meaning bridge
    try:
        from hg_core.ledger import emit
        from hg_core.scope_context import get_scope
        root = get_workspace_root()
        scope = get_scope()
        led_scope = {"type": scope.get("scope_type", "global"), "id": scope.get("scope_id", "default")}
        payload = {
            "decision_id": decision_id,
            "title": action,
            "chosen_option_id": "",
            "based_on_claim_ids": [],
            "value_weights": [],
            "context_ref": {},
            "produced_artifact_ids": [],
            "rationale": rationale,
        }
        emit(
            "DECISION_COMMITTED",
            "decision",
            decision_id,
            payload,
            scope=led_scope,
            workspace_root=root,
        )
    except Exception:
        pass

    return {
        "success": True,
        "decision": decision_record,
        "file": str(memory_file),
    }


def append_action_context(
    agent_id: str,
    action_id: str,
    context: str,
    date: Optional[str] = None,
) -> Dict[str, Any]:
    """Add context to an existing action."""
    memory_dir = get_automation_memory_dir(agent_id)
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    memory_file = memory_dir / f"{date}.md"
    timestamp = datetime.now().strftime("%H:%M")
    context_section = f"""

## Action Context - {timestamp}

**Action ID:** {action_id}
**Context:** {context}

---
"""
    try:
        with open(memory_file, "a", encoding="utf-8") as f:
            f.write(context_section)
        return {"success": True, "file": str(memory_file)}
    except IOError as e:
        return {"success": False, "error": str(e)}


def read_decision_history(
    agent_id: str,
    days: int = 7,
    search_query: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Read decision history for an agent."""
    try:
        shared = list_agent_decisions(agent_id, days=days, search_query=search_query)
        if shared:
            return shared
    except Exception:
        pass
    return []


def query_past_rationale(
    agent_id: str,
    action_keyword: str,
    days: int = 30,
) -> Optional[Dict[str, Any]]:
    """Find why a similar action was taken in the past."""
    decisions = read_decision_history(
        agent_id, days=days, search_query=action_keyword
    )
    return decisions[0] if decisions else None


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m hg_core.wrappers.decision_context <command> [args...]")
        print("Commands:")
        print("  record <agent_id> <action> <rationale> [alternatives] [tradeoffs] [context]")
        print("  query <agent_id> <keyword> [days]")
        print("  history <agent_id> [days]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "record":
        if len(sys.argv) < 5:
            print("Usage: record <agent_id> <action> <rationale>")
            sys.exit(1)
        agent_id = sys.argv[2]
        action = sys.argv[3]
        rationale = sys.argv[4]
        alternatives = sys.argv[5].split(",") if len(sys.argv) > 5 and sys.argv[5] else None
        tradeoffs = sys.argv[6] if len(sys.argv) > 6 else None
        context = sys.argv[7] if len(sys.argv) > 7 else None
        result = record_decision(agent_id, action, rationale, alternatives, tradeoffs, context)
        print(json.dumps(result, indent=2))

    elif command == "query":
        if len(sys.argv) < 4:
            print("Usage: query <agent_id> <keyword> [days]")
            sys.exit(1)
        agent_id = sys.argv[2]
        keyword = sys.argv[3]
        days = int(sys.argv[4]) if len(sys.argv) > 4 else 30
        result = query_past_rationale(agent_id, keyword, days)
        if result:
            print(json.dumps(result, indent=2))
        else:
            print("No matching decision found")

    elif command == "history":
        if len(sys.argv) < 3:
            print("Usage: history <agent_id> [days]")
            sys.exit(1)
        agent_id = sys.argv[2]
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 7
        decisions = read_decision_history(agent_id, days=days)
        print(json.dumps({"count": len(decisions), "decisions": decisions}, indent=2))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
