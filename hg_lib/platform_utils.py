"""
Platform utilities for Hydrogenuine. Fixes Windows UTF-8 encoding for CLI output.
"""

import io
import sys


def ensure_utf8_stdio() -> None:
    """
    Reconfigure stdout/stderr to use UTF-8 on Windows.
    Prevents encoding errors when printing Unicode to console.
    """
    if sys.platform != "win32":
        return
    try:
        if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != "utf-8":
            if hasattr(sys.stdout, "buffer") and sys.stdout.buffer:
                sys.stdout = io.TextIOWrapper(
                    sys.stdout.buffer, encoding="utf-8", errors="replace"
                )
        if not isinstance(sys.stderr, io.TextIOWrapper) or sys.stderr.encoding != "utf-8":
            if hasattr(sys.stderr, "buffer") and sys.stderr.buffer:
                sys.stderr = io.TextIOWrapper(
                    sys.stderr.buffer, encoding="utf-8", errors="replace"
                )
    except (AttributeError, ValueError, OSError):
        pass
