"""OEA compensation for bounded local capabilities."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

from hg_oea.config import OEAConfig
from hg_oea.types import CapabilityDefinition, CompensationStatus


def compensate_local_report(
    touched_resources: Tuple[str, ...],
    *,
    config: OEAConfig,
    capability: CapabilityDefinition,
) -> CompensationStatus:
    if capability.compensation_policy != "owned_path_cleanup":
        return "none"
    base = config.proof_dir.resolve()
    for resource in touched_resources:
        path = Path(resource).resolve()
        if base not in path.parents:
            return "failed"
        if path.exists() and path.is_file():
            try:
                path.unlink()
            except OSError:
                return "failed"
    return "completed"


__all__ = ["compensate_local_report"]
