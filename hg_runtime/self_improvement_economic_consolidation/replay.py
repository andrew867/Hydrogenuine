"""SIEW-03 / CAGI-65 replay."""

from __future__ import annotations

from hg_runtime.self_improvement_economic_consolidation.artifact_writer import (
    build_consolidation_artifacts,
)
from hg_runtime.self_improvement_economic_consolidation.fixtures import (
    fixture_all_receipts,
    fixture_proposal_to_task_link,
)


def replay_consolidation_artifacts() -> dict:
    return build_consolidation_artifacts(
        fixture_all_receipts(),
        [fixture_proposal_to_task_link()],
    )
