"""OEA Phase 1 stub executor entry point."""

from __future__ import annotations

from hg_oea.executor import OEAStubExecutor

# Backward-compatible alias used by the runtime handler registry.
OEAStub = OEAStubExecutor

__all__ = ["OEAStub", "OEAStubExecutor"]
