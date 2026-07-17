"""
Safe readers for optional automation files. Return sensible defaults when file is missing.
Used to avoid ENOENT when tasks expect "if file doesn't exist use empty structure".
"""

import json
from pathlib import Path
from typing import Any, Dict

from hg_lib.file_io import read_json


def load_skip_posts(workspace: Path, session_target: str) -> Dict[str, Any]:
    """
    Load skip_posts.json for a session (e.g. moltbook-engage). Returns {"post_ids": []}
    when the file is missing or invalid. Never raises.

    Caller must pass session_target from job_registry (e.g. get_session_target(task_name))
    so paths resolve correctly (e.g. automation-moltbook-engage, automation-aichan-auto-post).
    """
    path = workspace / "memory" / "automation" / session_target / "skip_posts.json"
    data = read_json(path, default={"post_ids": []}, create_if_missing=True)
    if not isinstance(data, dict):
        return {"post_ids": []}
    post_ids = data.get("post_ids")
    if not isinstance(post_ids, list):
        return {"post_ids": []}
    return {"post_ids": post_ids}
