"""ALC deterministic fixture replay."""

from __future__ import annotations

from typing import Any

from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.agent_lifecycle_controller.evaluator import process_alc_bundle
from hg_runtime.agent_lifecycle_controller.types import FIXTURE_CLOCK


def replay_fixture_stream(
    fixtures: list[dict[str, Any]],
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> tuple[list[dict[str, object]], str]:
    results: list[dict[str, object]] = []
    hashes: list[str] = []
    for row in fixtures:
        result = process_alc_bundle(row, observed_at=observed_at)
        results.append(result)
        receipt = result.get("alc_receipt")
        if isinstance(receipt, dict):
            hashes.append(str(receipt.get("record_hash", "")))
    combined = "|".join(hashes)
    return results, canonical_hash({"replay": combined})


__all__ = ["replay_fixture_stream"]
