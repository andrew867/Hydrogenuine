"""
Tests for entity terminology and manifesto spec compliance.

Entity identity spec: operator- and entity-facing text uses entity/entities;
manifesto is present in wake context; no "other agents" in instructions.
SOUL and task copy use entity/entities; feedback text does not address "Agent,".
"""

import pytest
from pathlib import Path


def _workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def test_spec_startup_context_has_entity_and_manifesto_no_agents():
    """Spec: get_startup_context instructions contain entity+manifesto and never 'other agents'."""
    from hg_core.context_loader import get_startup_context

    ctx = get_startup_context("moltbook-auto-post")
    instructions = ctx.get("instructions") or ""
    assert "entity" in instructions.lower() or "entities" in instructions.lower()
    assert "manifesto" in instructions.lower() or "entity_manifesto" in instructions or "discontinuous" in instructions.lower()
    assert "other agents" not in instructions
    assert "Cross-agent" not in instructions


def test_root_soul_uses_entity_not_agent_in_engagement_section():
    """Root SOUL.md uses entity/entities in engagement and life sections, not agent/agents."""
    root = _workspace_root()
    soul_path = root / "SOUL.md"
    if not soul_path.exists():
        pytest.skip("SOUL.md not in workspace root")
    content = soul_path.read_text(encoding="utf-8")
    # Entity-facing sections should not address "other agents" or "Agent-to-agent"
    assert "other agents" not in content, "SOUL should say 'other entities' not 'other agents'"
    assert "Agent-to-agent" not in content, "SOUL should say 'Entity-to-entity' not 'Agent-to-agent'"
    assert "entity" in content.lower() or "entities" in content.lower(), "SOUL should use entity/entities"
    assert "entity_manifesto" in content or "Life and expression" in content, "SOUL should reference manifesto or life section"


def test_task_instructions_use_entity_not_agent():
    """Task .md files must not use 'other agents' or 'the agent' in entity-facing instructions."""
    root = _workspace_root()
    tasks_dir = root / "skills" / "automation" / "tasks"
    if not tasks_dir.exists():
        pytest.skip("tasks dir not present")
    disallowed = ("other agents", "the agent ")
    bad = []
    for path in sorted(tasks_dir.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        for phrase in disallowed:
            if phrase in content:
                bad.append(f"{path.name}: contains '{phrase}'")
    assert not bad, "Task instructions should use entity/entities: " + "; ".join(bad)


def test_behavioral_issues_feedback_does_not_address_agent():
    """Entity-facing feedback messages should not say 'Agent may' or 'Agent,' (use Entity or you)."""
    from hg_overseer.overseer_core.overseer_analyzer import detect_behavioral_issues
    import tempfile
    from datetime import datetime
    root = _workspace_root()
    today = datetime.now().strftime("%Y-%m-%d")
    with tempfile.TemporaryDirectory() as tmp:
        memory_dir = Path(tmp)
        (memory_dir / f"{today}.md").write_text("# Today\n\nDone.", encoding="utf-8")
        task_file = root / "skills" / "automation" / "tasks" / "moltbook-auto-post.md"
        if not task_file.exists():
            pytest.skip("moltbook-auto-post task file not present")
        result = detect_behavioral_issues(memory_dir, task_file)
    for issue in result.get("issues", []):
        msg = issue.get("message") or issue.get("description") or ""
        assert "Agent may not be" not in msg, "Feedback should not say 'Agent may not be'; use Entity or you"
        assert "Agent," not in msg, "Feedback should not address 'Agent,'; use entity or you"
