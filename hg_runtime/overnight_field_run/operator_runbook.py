"""Operator runbook path reference."""

from __future__ import annotations

from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
RUNBOOK_PATH = WORKSPACE / "docs/runbooks/AGENT_ZERO_PHASE24_OVERNIGHT_FIELD_RUN_RUNBOOK.md"

__all__ = ["RUNBOOK_PATH"]
