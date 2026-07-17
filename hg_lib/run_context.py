"""
Run context for Hydrogenuine. Tracks run_id, workspace, job metadata.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


@dataclass
class RunContext:
    """Context for a single run (CLI invocation, task execution)."""

    run_id: str
    start_time: datetime
    workspace_root: Path
    job_id: str | None = None
    platform: str | None = None
    mode: str | None = None

    @classmethod
    def create(cls, workspace_root: Path, job_id: str | None = None, platform: str | None = None, mode: str | None = None) -> "RunContext":
        """Create a new run context."""
        return cls(
            run_id=str(uuid4()),
            start_time=datetime.now(timezone.utc),
            workspace_root=workspace_root,
            job_id=job_id,
            platform=platform,
            mode=mode,
        )
