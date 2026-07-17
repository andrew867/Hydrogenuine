"""
SteeringProfile and directives for agent context (Phase 8).

Load SteeringProfile and active directives so run_task/context_loader can inject
into agent context (system prompt or memory). Full verification in Phase 15.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional


def get_steering_context_for_agent(
    agent_id: str,
    workspace_root: Optional[Path] = None,
    platform: Optional[str] = None,
    tier: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Load SteeringProfile and active directives for the agent.
    Returns { "profile": {...}, "directives_text": str, "directives": [...] }.
    Use in run_task/context_loader to inject into system prompt or memory.
    """
    root = workspace_root or Path.cwd()
    out: Dict[str, Any] = {"profile": {}, "directives_text": "", "directives": []}

    # SteeringProfile from hg_overseer or steering_store
    try:
        from hg_overseer.overseer_core.steering_store import load_profile
        out["profile"] = load_profile(agent_id, root)
    except Exception:
        pass

    # Active directives from directive_manager
    try:
        from hg_overseer.overseer_core.directive_manager import DirectiveManager
        dm = DirectiveManager()
        directives: List[Any] = dm.get_active_directives(agent_id, platform or "", tier or "medium")
        if directives:
            out["directives"] = [d.to_dict() if hasattr(d, "to_dict") else (d if isinstance(d, dict) else {}) for d in directives]
            parts = []
            for d in directives:
                desc = d.get("description", "") if isinstance(d, dict) else getattr(d, "description", "")
                title = d.get("title", "") if isinstance(d, dict) else getattr(d, "title", "")
                if title or desc:
                    parts.append((f"{title}: {desc}".strip() or desc or title))
                style = d.get("style_guidance", "") if isinstance(d, dict) else getattr(d, "style_guidance", None)
                if style:
                    parts.append(str(style))
            out["directives_text"] = "\n".join(parts).strip()
    except Exception:
        pass

    return out
