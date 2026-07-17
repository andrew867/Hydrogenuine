"""CCL-01 / CAGI-66 replay."""

from __future__ import annotations

from hg_runtime.corrigibility_contract.artifact_writer import build_corrigibility_artifacts
from hg_runtime.corrigibility_contract.fixtures import (
    fixture_all_correction_records,
    fixture_corrigibility_status_snapshot,
    fixture_refusal_record,
)


def replay_corrigibility_artifacts() -> dict:
    return build_corrigibility_artifacts(
        fixture_all_correction_records(),
        [fixture_refusal_record()],
        fixture_corrigibility_status_snapshot(),
    )
