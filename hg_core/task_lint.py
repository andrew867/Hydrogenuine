"""
CLI for task file validation. Run: hg-task-lint or python -m hg_core.task_lint
"""

import sys
from pathlib import Path

from hg_lib.config import get_workspace_root
from hg_core.task_validator import validate_all_tasks


def main() -> int:
    """Lint all task files under skills/automation/tasks/. Exit 0 if all pass."""
    workspace = get_workspace_root()
    all_valid, results = validate_all_tasks(workspace)
    for path, errors, warnings in results:
        try:
            rel = path.relative_to(workspace)
        except ValueError:
            rel = path
        if errors:
            print(f"{rel}: FAIL")
            for e in errors:
                print(f"  error: {e}")
        if warnings:
            for w in warnings:
                print(f"{rel}: warning: {w}")
        if not errors and not warnings:
            print(f"{rel}: OK")
        elif not errors:
            print(f"{rel}: OK (with warnings)")
    return 0 if all_valid else 1


if __name__ == "__main__":
    sys.exit(main())
