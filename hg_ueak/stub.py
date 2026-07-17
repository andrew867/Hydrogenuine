"""UEAK Phase 1 commit scaffold entry point."""

from __future__ import annotations

from hg_ueak.commit_scaffold import CommitScaffold

# Backward-compatible alias used by the runtime handler registry.
UEAKStub = CommitScaffold

__all__ = ["CommitScaffold", "UEAKStub"]
