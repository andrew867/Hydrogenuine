"""
Memory file data contracts: validation for posts.json and decisions.json.

On invalid data we log a warning; callers still write (best-effort) to avoid blocking entity autonomy.
See docs/specs/memory_and_feedback_schemas_spec.md.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def validate_posts_file(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate posts.json root structure.
    Required: dict with "posts" key (list). Each post must be a dict.
    """
    if not isinstance(data, dict):
        return False, "expected dict"
    if "posts" not in data:
        return False, "missing posts key"
    posts = data["posts"]
    if not isinstance(posts, list):
        return False, "posts must be list"
    for i, item in enumerate(posts):
        if not isinstance(item, dict):
            return False, f"posts[{i}] must be dict"
    return True, None


def validate_decisions_file(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate decisions.json root structure.
    Required: dict with "decisions" key (list). Each decision must have action (str) and rationale (str).
    """
    if not isinstance(data, dict):
        return False, "expected dict"
    if "decisions" not in data:
        return False, "missing decisions key"
    decisions = data["decisions"]
    if not isinstance(decisions, list):
        return False, "decisions must be list"
    for i, item in enumerate(decisions):
        if not isinstance(item, dict):
            return False, f"decisions[{i}] must be dict"
        if "action" not in item:
            return False, f"decisions[{i}] missing action"
        if not isinstance(item.get("action"), str):
            return False, f"decisions[{i}] action must be string"
        if "rationale" not in item:
            return False, f"decisions[{i}] missing rationale"
        if not isinstance(item.get("rationale"), str):
            return False, f"decisions[{i}] rationale must be string"
    return True, None


def validate_and_warn_posts_file(data: Dict[str, Any]) -> bool:
    """Validate posts file; log warning if invalid. Returns True if valid."""
    ok, err = validate_posts_file(data)
    if not ok:
        logger.warning("posts.json validation failed: %s", err)
    return ok


def validate_and_warn_decisions_file(data: Dict[str, Any]) -> bool:
    """Validate decisions file; log warning if invalid. Returns True if valid."""
    ok, err = validate_decisions_file(data)
    if not ok:
        logger.warning("decisions.json validation failed: %s", err)
    return ok
