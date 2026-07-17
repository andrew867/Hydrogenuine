"""Thin gate wrapper for overnight QA readiness."""

from __future__ import annotations

from .readiness import run_readiness_gate


def run_gate(**kwargs) -> dict:
    return run_readiness_gate(**kwargs)
