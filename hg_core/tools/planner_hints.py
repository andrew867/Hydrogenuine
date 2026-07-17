"""
Planner hints for entity tools (Social Media Entity Tools).
Inject into entity/agent startup context so task decomposition can pick tools intentionally.
"""

PLANNER_BOOTSTRAP_HINT = """
Available tool families:
- python_sandbox, execute bounded Python for analysis or transformation
- workspace_canvas, create or update code and document workspaces
- file_writer, write files and package downloadable outputs
- browser_runtime, supervised web interaction with screenshots and trace
- social_reddit, search, draft, comment, submit posts with approval gate
- social_x, search, draft, reply, submit posts with approval gate
- social_facebook, search, draft, reply, submit posts with approval gate

Rules:
- any external write action requires explicit operator approval
- login and MFA require supervised browser mode
- prefer preview then approval then submit
- always attach proof artifacts for write actions
""".strip()


def get_planner_bootstrap_context() -> dict:
    """Return a dict to merge into entity/planner context so task decomposition sees tool awareness."""
    return {"planner_hint": PLANNER_BOOTSTRAP_HINT}


def get_planner_hint_for_tool(tool_id: str) -> str | None:
    """Optional per-tool hint for the planner. Returns None if no specific hint."""
    hints = {
        "social_reddit": "Use social_reddit for Reddit posts and comments; preview then request approval before submit.",
        "social_x": "Use social_x for X (Twitter) posts and replies; preview then request approval before submit.",
        "social_facebook": "Use social_facebook for Facebook posts and replies; preview then request approval before submit.",
        "browser_runtime": "Use browser_runtime for supervised web actions; supports screenshot and pause for human gate.",
    }
    return hints.get(tool_id)
