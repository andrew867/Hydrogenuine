"""
Read and Acknowledge Overseer Feedback.

CLI entry point for agents to read and acknowledge overseer feedback.
Delegates to the same logic as the legacy script (feedback_tracker + feedback_action_executor).
"""

from __future__ import annotations

import sys


def main() -> None:
    # Delegate to legacy implementation so we keep one codebase for feedback_action_executor
    from skills.automation.wrappers.read_and_acknowledge_feedback import main as _main
    _main()


if __name__ == "__main__":
    main()  # legacy main() calls sys.exit()
