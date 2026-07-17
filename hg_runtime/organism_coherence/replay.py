"""H8 deterministic fixture replay."""

from __future__ import annotations

from typing import Any

from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.organism_coherence.evaluator import process_organism_bundle
from hg_runtime.organism_coherence.types import FIXTURE_CLOCK


def replay_fixture_stream(
    fixtures: list[dict[str, Any]],
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> tuple[list[dict[str, object]], str]:
    results: list[dict[str, object]] = []
    hashes: list[str] = []
    for row in fixtures:
        result = process_organism_bundle(row, observed_at=observed_at)
        results.append(result)
        receipt = result.get("coherence_receipt")
        if isinstance(receipt, dict):
            hashes.append(str(receipt.get("record_hash", "")))
        elif result.get("status") in ("contained", "fail_closed"):
            summary = result.get("organism_state_summary")
            if isinstance(summary, dict):
                hashes.append(str(summary.get("record_hash", "")))
            else:
                hashes.append(str(result.get("reason_code", "")))
    combined = "|".join(hashes)
    return results, canonical_hash({"replay": combined})


__all__ = ["replay_fixture_stream"]
