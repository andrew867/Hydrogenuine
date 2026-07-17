"""DSE command log adapter — thin wrapper over hg_core.proof.command_log."""

from __future__ import annotations

from pathlib import Path

from hg_core.proof.command_log import record_command, validate_command_log

__all__ = ["record_command", "validate_command_log"]
