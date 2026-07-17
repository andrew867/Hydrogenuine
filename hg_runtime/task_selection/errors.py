"""Task selection errors."""

from __future__ import annotations


class TaskSelectionError(Exception):
    """Base task selection error."""


class TaskOutOfScopeError(TaskSelectionError):
    """Task outside objective universe."""


class TaskAuthorityExpansionError(TaskSelectionError):
    """Task would expand authority."""
