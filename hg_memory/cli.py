"""
CLI for hg_memory: hg-memory-index (run indexing job).
"""

import json
import sys

from hg_memory import run_indexing_job


def main() -> int:
    """Run indexing job for all agents (cron entry point)."""
    result = run_indexing_job()
    print(json.dumps(result, indent=2))
    return 0 if result.get("total_errors", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
