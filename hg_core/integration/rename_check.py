"""
Control Surface Pack 11: Rename check — CI fails if disallowed brand strings appear in tracked files.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from .branding import DISALLOWED_BRAND_STRINGS


def check_no_disallowed_brand_strings(
    workspace_root: Path,
    paths: List[Path] | None = None,
    exclude_paths: List[Path] | None = None,
) -> Tuple[bool, List[str]]:
    """
    Scan paths (or workspace_root) for disallowed brand strings (e.g. YOUR_NEW_NAME_HERE).
    exclude_paths: paths to skip (e.g. files that define DISALLOWED_BRAND_STRINGS).
    Returns (passed, list of violation messages).
    """
    root = Path(workspace_root)
    if paths is None:
        paths = [root]
    exclude = set(Path(p).resolve() for p in (exclude_paths or []))
    violations: List[str] = []
    for start in paths:
        if not start.exists():
            continue
        if start.is_file():
            files = [start]
        else:
            files = list(start.rglob("*.py")) + list(start.rglob("*.md")) + list(start.rglob("*.yaml")) + list(start.rglob("*.yml"))
        for f in files:
            if f.resolve() in exclude:
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
                for disallowed in DISALLOWED_BRAND_STRINGS:
                    if disallowed in text:
                        violations.append(f"{f}: contains disallowed string '{disallowed}'")
            except (OSError, UnicodeDecodeError):
                continue
    return (len(violations) == 0, violations)
